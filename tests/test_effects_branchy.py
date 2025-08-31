# tests/test_effects_branchy.py
import pytest
from starrealms.effects import apply_effects


class DummyAgent:
    """Simple agent that always picks the first thing."""
    def choose_card(self, zone, prompt=None):
        return zone[0] if zone else None

    def choose_option(self, options, prompt=None):
        return options[0] if options else None


# ---------- Selection / Opponent interactions ----------

@pytest.mark.xfail(strict=False, reason="depends on resolver wiring for opponent choices")
def test_opponent_discards_forced(game, p1, p2):
    # Opponent has 2 cards; their agent chooses the first to discard.
    p2.hand = [{"name": "Scout"}, {"name": "Viper"}]
    p2.agent = DummyAgent()
    start = len(p2.hand)
    apply_effects({"type": "opponent_discards", "amount": 1}, p1, p2, game)
    assert len(p2.hand) == start - 1


@pytest.mark.xfail(strict=False, reason="depends on resolver wiring for choose_one")
def test_choose_one_trade_vs_combat(game, p1, p2):
    p1.agent = DummyAgent()
    before_trade, before_combat = p1.trade_pool, p1.combat_pool
    eff = {
        "type": "choose_one",
        "options": [
            {"label": "Trade", "effects": [{"type": "trade", "amount": 2}]},
            {"label": "Combat", "effects": [{"type": "combat", "amount": 3}]},
        ],
    }
    apply_effects(eff, p1, p2, game)
    # Dummy picks first option → +2 trade expected
    assert p1.trade_pool == before_trade + 2
    assert p1.combat_pool == before_combat


# ---------- Control flow / meta effects ----------

@pytest.mark.xfail(strict=False, reason="repeat meta-effect may be unimplemented")
def test_repeat_runs_effect_multiple_times(game, p1, p2):
    apply_effects({"type": "repeat", "times": 3, "effect": {"type": "trade", "amount": 1}}, p1, p2, game)
    assert p1.trade_pool >= 3  # allow >= in case other effects add too


@pytest.mark.xfail(strict=False, reason="count meta-effect may be unimplemented")
def test_count_per_ship_in_play_adds_trade(game, p1, p2):
    # 2 ships in play → +2 trade if 'count per ship' exists
    p1.in_play = [{"name": "Scout", "type": "ship"}, {"name": "Viper", "type": "ship"}]
    before = p1.trade_pool
    eff = {"type": "count", "zone": "in_play", "per": "ship", "effect": {"type": "trade", "amount": 1}}
    apply_effects(eff, p1, p2, game)
    assert p1.trade_pool >= before + 2


# ---------- If / conditional branches ----------

def test_if_faction_in_play_true_branch(game, p1, p2):
    # Blob in play should satisfy condition and add combat.
    p1.in_play.append({"name": "Blob Fighter", "faction": "Blob", "type": "ship"})
    before_trade, before_combat = p1.trade_pool, p1.combat_pool
    eff = {
        "type": "if",
        "condition": {"type": "faction_in_play", "faction": "Blob"},
        "then": [{"type": "combat", "amount": 5}],
        "else": [{"type": "trade", "amount": 5}],
    }
    apply_effects(eff, p1, p2, game)
    assert p1.combat_pool == before_combat + 5
    assert p1.trade_pool == before_trade


# ---------- Trade row interactions ----------

@pytest.mark.xfail(strict=False, reason="acquire_free selection may require resolver agent")
def test_acquire_free_from_trade_row(game, p1, p2):
    p1.agent = DummyAgent()
    c1 = {"name": "Cutter", "cost": 2}
    c2 = {"name": "Corvette", "cost": 2}
    game.trade_row = [c1, c2]
    apply_effects({"type": "acquire_free"}, p1, p2, game)
    # Dummy picks first → card ends up in a gain zone (discard/hand/bases/topdeck)
    assert (c1 in p1.discard_pile) or (c1 in p1.hand) or (c1 in p1.bases) or (p1.deck and p1.deck[0] is c1)
    assert c1 not in game.trade_row


@pytest.mark.xfail(strict=False, reason="acquire_to_topdeck may require resolver agent")
def test_acquire_to_topdeck_from_trade_row(game, p1, p2):
    p1.agent = DummyAgent()
    c = {"name": "Battlecruiser", "cost": 6}
    game.trade_row = [c]
    apply_effects({"type": "acquire_to_topdeck"}, p1, p2, game)
    assert p1.deck and p1.deck[0] is c


@pytest.mark.xfail(strict=False, reason="destroy_trade_row may require resolver agent")
def test_destroy_trade_row_single_slot(game, p1, p2):
    p1.agent = DummyAgent()
    c = {"name": "Freighter", "cost": 4}
    game.trade_row = [c]
    apply_effects({"type": "destroy_trade_row"}, p1, p2, game)
    assert c not in game.trade_row


# ---------- Base interaction / removal ----------

def test_destroy_base_prioritizes_outpost(game, p1, p2):
    # No resolver needed if effect auto-picks outpost first.
    normal = {"name": "Base B", "type": "base", "defense": 5, "outpost": False}
    outpost = {"name": "Outpost A", "type": "base", "defense": 3, "outpost": True}
    p2.bases[:] = [normal, outpost]
    apply_effects({"type": "destroy_base"}, p1, p2, game)
    names = [b["name"] for b in p2.bases]
    assert "Outpost A" not in names
    assert "Base B" in names


@pytest.mark.xfail(strict=False, reason="scrap_from_trade_row may require resolver agent")
def test_scrap_from_trade_row_removes_card(game, p1, p2):
    p1.agent = DummyAgent()
    c = {"name": "Explorer", "cost": 2}
    game.trade_row = [c]
    apply_effects({"type": "scrap_from_trade_row"}, p1, p2, game)
    assert c not in game.trade_row