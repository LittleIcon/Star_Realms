# tests/test_unified_dispatcher_unit.py
import types
import pytest

from starrealms.engine.unified_dispatcher import GameAPI, AbilityDispatcher


# ---- Minimal fake Game + UI used by GameAPI ----
class FakeGame:
    def __init__(self):
        # per-player counters
        self.trade = {}
        self.combat = {}
        self.authority = {}
        self.draws = {}
        self.forced_discards = {}
        self.zones = {}  # zones[player_name][zone_name] -> list of cards
        self.scrapped = []
        self.acquired = []   # (player, idx, dest)
        self.destroyed_traderow = []  # indices
        self.destroy_enemy_bases = []  # (owner, idx)
        self.recorded_played = []  # (player, card)

        # market
        self.trade_row = []
        self.trade_deck = []
        self._trade_row_filter_strategy = "first"  # "first" returns [0] if row non-empty

    def _inc(self, d, k, v=1):
        d[k] = d.get(k, 0) + v

    # --- API methods GameAPI will call ---
    def add_trade(self, player, amount):     self._inc(self.trade, player, amount)
    def add_combat(self, player, amount):    self._inc(self.combat, player, amount)
    def add_authority(self, player, amount): self._inc(self.authority, player, amount)
    def draw(self, player):                  self._inc(self.draws, player, 1)

    def force_discard(self, target, n=1):
        self._inc(self.forced_discards, target, n)
        # If there are cards, discard from 'hand' zone
        hand = self.zones.setdefault(target, {}).setdefault("hand", [])
        for _ in range(n):
            if hand:
                hand.pop(0)

    def list_zone(self, player, zone):
        return self.zones.setdefault(player, {}).setdefault(zone, [])

    def scrap_card(self, player, zone, index):
        pile = self.zones.setdefault(player, {}).setdefault(zone, [])
        if 0 <= index < len(pile):
            self.scrapped.append(pile.pop(index))

    def trade_row_filtered(self, filt):
        # super simple matcher: return first index if exists
        return [0] if self.trade_row else []

    def cost_of_trade_row(self, idx):
        if 0 <= idx < len(self.trade_row):
            return int(self.trade_row[idx].get("cost", 0))
        return 0

    def spend_trade(self, player, cost):
        # not used in these tests
        pass

    def acquire_from_trade_row(self, player, idx, destination="discard"):
        if 0 <= idx < len(self.trade_row):
            c = self.trade_row.pop(idx)
            self.acquired.append((player, idx, destination, c))

    def destroy_trade_row(self, idx):
        if 0 <= idx < len(self.trade_row):
            self.destroyed_traderow.append(idx)
            self.trade_row.pop(idx)

    def destroy_enemy_base(self, owner, base_idx):
        self.destroy_enemy_bases.append((owner, base_idx))

    def record_played_this_turn(self, player, card):
        self.recorded_played.append((player, card))


class FakeUI:
    def __init__(self):
        self.notifications = []
        self.chosen_labels = 0
        self.trade_row_pick = 0
        self.enemy_base_pick = 0
        # for pick_multi_cards returning (zone, idx, card) tuples
        self.multi_picks = []

    def notify(self, msg):
        self.notifications.append(msg)

    def pick_from_labels(self, labels, prompt="Choose one:"):
        # always pick first
        self.chosen_labels = 0
        return 0 if labels else None

    def pick_trade_row(self, filter=None):
        return self.trade_row_pick

    def pick_enemy_base(self, owner):
        return self.enemy_base_pick

    def pick_multi_cards(self, player, zones, max_count, allow_less, prompt):
        # Return pre-baked picks if available
        return list(self.multi_picks)[:max_count]


# ---------------------------- Tests ----------------------------

def make_api():
    game = FakeGame()
    ui = FakeUI()
    api = GameAPI(game, ui)
    return api, game, ui


def test_start_turn_and_used_abilities_reset():
    api, game, ui = make_api()
    api.mark_used("P1", "ability-1")
    assert not api.can_use("P1", "ability-1")  # used
    api.start_turn("P1")
    assert api.can_use("P1", "ability-1")      # cleared


def test_register_unregister_and_fire_hooks():
    api, game, ui = make_api()
    called = {"n": 0}

    def hook(api_obj, player, **payload):
        called["n"] += 1

    api.register_hook("P1", "on_ship_played", hook, source="CardX")
    api.fire("P1", "on_ship_played", ship={"name": "Scout"})
    assert called["n"] == 1

    api.unregister_hooks_from_source("P1", "CardX")
    api.fire("P1", "on_ship_played", ship={"name": "Scout"})
    assert called["n"] == 1  # unchanged


def test_faction_in_play_min_and_scope():
    api, game, ui = make_api()
    # default list_zone returns []
    assert api.faction_in_play("P1", "Blob", 1, "in_play") is False

    # Seed in_play with a Blob and a Trade Federation
    z = game.zones.setdefault("P1", {})
    z["in_play"] = [{"name": "Blob Fighter", "faction": "Blob"},
                    {"name": "Cutter", "faction": "Trade Federation"}]
    assert api.faction_in_play("P1", "Blob", 1, "in_play") is True
    assert api.faction_in_play("P1", "Blob", 2, "in_play") is False


def test_on_card_enter_play_continuous_and_on_play_and_record():
    api, game, ui = make_api()
    disp = AbilityDispatcher(api)

    # Put a Blob card in-play list for the condition to pass
    game.zones.setdefault("P1", {})["in_play"] = [{"name": "Blob Fighter", "faction": "Blob"}]

    card = {
        "name": "CardY",
        "abilities": [
            {"trigger": "on_play",
             "condition": {"faction_in_play": {"faction": "Blob", "min": 1, "scope": "in_play"}},
             "effects": [{"type": "combat", "amount": 3}]},
            {"trigger": "continuous:on_ship_played",
             "effects": [{"type": "trade", "amount": 1}]}
        ]
    }

    disp.on_card_enter_play("P1", card)

    # on_play applied
    assert game.combat.get("P1", 0) == 3
    # continuous hook registered -> fire by simulating ship played
    disp.on_ship_played("P1", {"name": "Scout"})
    assert game.trade.get("P1", 0) == 1

    # recorded into game
    assert ("P1", card) in game.recorded_played


def test_on_turn_start_triggers_effects():
    api, game, ui = make_api()
    disp = AbilityDispatcher(api)

    # Seed player's in_play with a card that has on_turn_start draw 2
    game.zones.setdefault("P1", {})["in_play"] = [{
        "name": "StartBase",
        "abilities": [
            {"trigger": "on_turn_start", "effects": [{"type": "draw", "amount": 2}]}
        ],
    }]

    disp.on_turn_start("P1")
    assert game.draws.get("P1", 0) == 2
    # also start_turn() was called and usage cleared (sanity check)
    api.mark_used("P1", "x")
    disp.on_turn_start("P1")  # will clear before applying again
    assert api.can_use("P1", "x")


def test_activate_card_once_per_turn_and_id_filter():
    api, game, ui = make_api()
    disp = AbilityDispatcher(api)
    card = {
        "name": "Activator",
        "abilities": [
            {"trigger": "activated", "id": "a1", "frequency": {"once_per_turn": True},
             "effects": [{"type": "trade", "amount": 2}]},
            {"trigger": "activated", "id": "a2", "frequency": {"once_per_turn": False},
             "effects": [{"type": "combat", "amount": 1}]}
        ]
    }

    # Use id 'a1' twice -> second should notify and not apply
    disp.activate_card("P1", card, ability_id="a1")
    disp.activate_card("P1", card, ability_id="a1")
    assert game.trade.get("P1", 0) == 2
    assert "Already used this ability" in (ui.notifications[-1] if ui.notifications else "")

    # Use id 'a2' twice -> allowed (no once_per_turn)
    disp.activate_card("P1", card, ability_id="a2")
    disp.activate_card("P1", card, ability_id="a2")
    assert game.combat.get("P1", 0) == 2


def test_scrap_activate_applies_and_notify_when_missing():
    api, game, ui = make_api()
    disp = AbilityDispatcher(api)

    has_scrap = {
        "name": "Scrapper",
        "abilities": [{"trigger": "scrap_activated", "effects": [{"type": "authority", "amount": 5}]}]
    }
    disp.scrap_activate("P1", has_scrap)
    assert game.authority.get("P1", 0) == 5

    ui.notifications.clear()
    no_scrap = {"name": "NoScrap", "abilities": [{"trigger": "activated"}]}
    disp.scrap_activate("P1", no_scrap)
    assert "No scrap-activated ability" in (ui.notifications[-1] if ui.notifications else "")


def test_apply_effects_scrap_selected_draw_from_count_choose_one_and_market_ops():
    api, game, ui = make_api()
    disp = AbilityDispatcher(api)

    # Seed hand with 3 cards and pre-bake pick_multi to scrap 2 of them.
    hand = [{"name": "H0"}, {"name": "H1"}, {"name": "H2"}]
    game.zones.setdefault("P1", {})["hand"] = hand
    # Use (0, 0) indices to avoid shift after first pop
    ui.multi_picks = [("hand", 0, hand[0]), ("hand", 0, hand[1])]

    # Also seed 'where' zone for count
    game.zones["P1"]["in_play"] = [{"name": "S1", "type": "ship"}, {"name": "B1", "type": "base"},
                                   {"name": "S2", "type": "ship"}]

    # Market contents
    game.trade_row = [{"name": "RowA", "cost": 3}, {"name": "RowB", "cost": 2}]
    game.trade_deck = [{"name": "Refill"}]
    ui.trade_row_pick = 1  # pick RowB

    # Enemy base pick
    ui.enemy_base_pick = 0

    # Compose a sequence of effects that runs through many branches
    effects = [
        {"type": "scrap_selected", "max": 2, "zones": ["hand"], "store_as": "scrapped_n"},
        {"type": "count", "where": "in_play", "filter": {"type": "ship"}, "store_as": "ship_count"},
        {"type": "draw_from", "key": "scrapped_n"},  # draw equal to scrapped
        {"type": "choose_one", "options": [
            {"label": "Trade", "effects": [{"type": "trade", "amount": 2}]},
            {"label": "Combat", "effects": [{"type": "combat", "amount": 3}]},
        ]},
        {"type": "acquire_free", "destination": "discard"},
        {"type": "destroy_trade_row"},
        {"type": "destroy_base", "owner": "opponent"},
        {"type": "unknown_type_should_notify"},
    ]

    # Provide enemy bases for destroy_base to target (the dispatcher asks UI for index)
    disp._apply_effects("P1", effects)

    # scrap_selected → two cards scrapped from hand
    assert len(game.scrapped) == 2
    # count (ships) stored, draw_from uses scrapped_n (2) → 2 draws
    assert game.draws.get("P1", 0) >= 2
    # choose_one default picks first option → +2 trade
    assert game.trade.get("P1", 0) >= 2
    # acquire_free & destroy_trade_row routed to game
    assert any(t[0] == "P1" and t[1] == ui.trade_row_pick for t in game.acquired)
    assert ui.trade_row_pick in game.destroyed_traderow
    # destroy_base routed
    assert ("opponent", ui.enemy_base_pick) in game.destroy_enemy_bases
    # unknown effect → notify
    assert any("Unknown effect type" in msg for msg in ui.notifications)


def test_on_card_leave_play_unregisters_continuous_hooks():
    api, game, ui = make_api()
    disp = AbilityDispatcher(api)
    card = {
        "name": "ContBase",
        "abilities": [{"trigger": "continuous:on_ship_played", "effects": [{"type": "trade", "amount": 1}]}],
    }
    disp.on_card_enter_play("P1", card)
    # hook registered under source "ContBase"
    assert "on_ship_played" in api.hooks.get("P1", {})
    disp.on_card_leave_play("P1", card)
    # entries for source removed
    assert [src for (src, _fn) in api.hooks.get("P1", {}).get("on_ship_played", [])] == []


def test_condition_blocking_prevents_on_play_effects():
    api, game, ui = make_api()
    disp = AbilityDispatcher(api)
    # No Blob in zones -> condition false
    card = {
        "name": "NeedsBlob",
        "abilities": [
            {"trigger": "on_play",
             "condition": {"faction_in_play": {"faction": "Blob", "min": 1, "scope": "in_play"}},
             "effects": [{"type": "combat", "amount": 5}]}
        ],
    }
    disp.on_card_enter_play("P1", card)
    assert game.combat.get("P1", 0) == 0