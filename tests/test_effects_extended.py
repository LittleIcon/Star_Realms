# tests/test_effects_extended.py
import pytest
from starrealms.effects import apply_effects

# --- helpers ---
class DummyAgent:
    def choose_option(self, options, prompt=None):
        return options[0]

    def choose_card(self, zone, prompt=None):
        return zone[0]


class DummyDispatcher:
    def __init__(self):
        self.registered = []
        self.unregistered = []

    def register_hook(self, owner, hook, card):
        self.registered.append((owner, hook, card))

    def unregister_hooks(self, owner, card):
        self.unregistered.append((owner, card))


# --- primitive edge cases ---

def test_draw_with_empty_deck_triggers_reshuffle(game, p1, p2):
    # move one card to discard, clear deck
    discard_card = {"name": "Scout"}
    p1.discard_pile.append(discard_card)
    p1.deck.clear()
    apply_effects({"type": "draw", "amount": 1}, p1, p2, game)
    assert discard_card in p1.hand


def test_discard_with_empty_hand_noop(game, p1, p2):
    p1.hand.clear()
    apply_effects({"type": "discard", "amount": 1}, p1, p2, game)
    assert p1.hand == []  # no crash


def test_scrap_selected_no_eligible_cards_noop(game, p1, p2):
    p1.hand.clear()
    p1.agent = DummyAgent()
    apply_effects({"type": "scrap_selected", "zone": "hand"}, p1, p2, game)
    assert p1.scrap_heap == []


# --- choices & conditionals ---
@pytest.mark.needs_resolver
@pytest.mark.xfail(strict=False, reason="requires resolver + agent path")
def test_choose_one_agent_picks_first(game, p1, p2):
    p1.agent = DummyAgent()
    eff = {
        "type": "choose_one",
        "options": [
            {"label": "Trade", "effects": [{"type": "trade", "amount": 2}]},
            {"label": "Combat", "effects": [{"type": "combat", "amount": 3}]},
        ],
    }
    apply_effects(eff, p1, p2, game)
    assert p1.trade_pool == 2
    assert p1.combat_pool == 0


def test_if_condition_true_with_blob_in_play(game, p1, p2):
    blob_card = {"name": "Blob Fighter", "faction": "Blob"}
    p1.in_play.append(blob_card)
    eff = {
        "type": "if",
        "condition": {"type": "faction_in_play", "faction": "Blob"},
        "then": [{"type": "combat", "amount": 5}],
        "else": [{"type": "trade", "amount": 5}],
    }
    apply_effects(eff, p1, p2, game)
    assert p1.combat_pool == 5
    assert p1.trade_pool == 0


# --- board-interaction effects ---

def test_destroy_base_respects_outpost(game, p1, p2):
    p1.agent = DummyAgent()
    normal = {"name": "Base B", "type": "base", "defense": 5, "outpost": False}
    outpost = {"name": "Outpost A", "type": "base", "defense": 3, "outpost": True}
    p2.bases[:] = [normal, outpost]

    eff = {"type": "destroy_base"}
    apply_effects(eff, p1, p2, game)

    names = [c["name"] for c in p2.bases]
    assert "Outpost A" not in names
    assert "Base B" in names


def test_acquire_free_places_in_discard(game, p1, p2):
    p1.agent = DummyAgent()
    card = {"name": "Freighter", "cost": 4}
    game.trade_row = [card]
    apply_effects({"type": "acquire_free"}, p1, p2, game)
    assert card in p1.discard_pile or card in p1.hand or card in p1.bases


def test_acquire_to_topdeck_places_on_deck(game, p1, p2):
    p1.agent = DummyAgent()
    card = {"name": "Battlecruiser", "cost": 6}
    game.trade_row = [card]
    apply_effects({"type": "acquire_to_topdeck"}, p1, p2, game)
    assert p1.deck and p1.deck[0]["name"] == "Battlecruiser"


def test_destroy_trade_row_removes_card(game, p1, p2):
    p1.agent = DummyAgent()
    card = {"name": "Cutter", "cost": 2}
    game.trade_row = [card]
    apply_effects({"type": "destroy_trade_row"}, p1, p2, game)
    assert card not in game.trade_row


# --- hooks & bonuses ---

def test_register_and_unregister_hooks(game, p1, p2):
    game.dispatcher = DummyDispatcher()
    card = {"name": "Test Hook Card"}
    apply_effects({"type": "register_hook", "hook": "on_play", "card": card}, p1, p2, game)
    apply_effects({"type": "unregister_hooks", "card": card}, p1, p2, game)
    assert ("P1", "on_play", card) in game.dispatcher.registered
    assert ("P1", card) in game.dispatcher.unregistered


def test_per_ship_combat_bonus_applies_when_playing_ship(game, p1, p2):
    # give +1 per ship effect
    apply_effects({"type": "per_ship_combat_bonus", "amount": 1}, p1, p2, game)
    ship = {"name": "Scout", "type": "ship"}
    before = p1.combat_pool
    p1.play_card(ship, p2, game)
    after = p1.combat_pool
    assert after == before + 1
    
def test_discard_then_draw_with_enough_cards(game, p1, p2):
    # Fill hand with 3 dummy cards
    p1.hand = [{"name": f"Card{i}"} for i in range(3)]
    start_len = len(p1.hand)
    apply_effects({"type": "discard_then_draw", "amount": 2}, p1, p2, game)
    # Net hand size should be unchanged (2 discarded, 2 drawn)
    assert len(p1.hand) == start_len


def test_opponent_discards_forced(game, p1, p2):
    p2.hand = [{"name": "Scout"}, {"name": "Viper"}]
    p2.agent = type("A", (), {"choose_card": lambda self, zone, prompt=None: zone[0]})()
    start_len = len(p2.hand)
    apply_effects({"type": "opponent_discards", "amount": 1}, p1, p2, game)
    assert len(p2.hand) == start_len - 1


def test_repeat_effect_runs_multiple_times(game, p1, p2):
    eff = {"type": "repeat", "times": 3, "effect": {"type": "trade", "amount": 1}}
    apply_effects(eff, p1, p2, game)
    assert p1.trade_pool == 3


def test_draw_from_opponent_discard(game, p1, p2):
    card = {"name": "Scout"}
    p2.discard_pile.append(card)
    eff = {"type": "draw_from", "source": "opponent_discard"}
    apply_effects(eff, p1, p2, game)
    assert card in p1.hand
    assert card not in p2.discard_pile


def test_count_effect_adds_trade_per_card(game, p1, p2):
    # put 2 ships in play
    p1.in_play = [{"name": "Scout"}, {"name": "Viper"}]
    eff = {
        "type": "count",
        "zone": "in_play",
        "per": "ship",
        "effect": {"type": "trade", "amount": 1},
    }
    apply_effects(eff, p1, p2, game)
    assert p1.trade_pool == 2