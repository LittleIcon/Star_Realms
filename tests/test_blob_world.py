# tests/test_blob_world.py
import pytest
from starrealms.engine.unified_dispatcher import GameAPI, AbilityDispatcher


# --- minimal fakes (same flavor as test_unified_dispatcher_unit.py) ---
class _FakeGame:
    def __init__(self):
        self.trade = {}
        self.combat = {}
        self.authority = {}
        self.draws = {}
        self.zones = {}  # zones[player][zone] -> list of cards

    def _inc(self, d, k, v=1):
        d[k] = d.get(k, 0) + v

    def add_trade(self, player, amount):     self._inc(self.trade, player, amount)
    def add_combat(self, player, amount):    self._inc(self.combat, player, amount)
    def add_authority(self, player, amount): self._inc(self.authority, player, amount)
    def draw(self, player):                  self._inc(self.draws, player, 1)

    def list_zone(self, player, zone):
        return self.zones.setdefault(player, {}).setdefault(zone, [])

    # extras to satisfy GameAPI interface (unused here)
    def force_discard(self, *a, **k): pass
    def scrap_card(self, *a, **k): pass
    def trade_row_filtered(self, *a, **k): return []
    def cost_of_trade_row(self, *a, **k): return 0
    def spend_trade(self, *a, **k): pass
    def acquire_from_trade_row(self, *a, **k): pass
    def destroy_trade_row(self, *a, **k): pass
    def destroy_enemy_base(self, *a, **k): pass
    def record_played_this_turn(self, *a, **k): pass


class _FakeUI:
    def __init__(self, pick_index=0):
        self._pick_index = pick_index  # which option to choose in choose_one

    def pick_from_labels(self, labels, prompt="Choose one:"):
        if not labels:
            return None
        return min(max(self._pick_index, 0), len(labels) - 1)


def _make_env(pick_index=0):
    game = _FakeGame()
    ui = _FakeUI(pick_index=pick_index)
    api = GameAPI(game, ui)
    disp = AbilityDispatcher(api)
    return game, ui, api, disp


def _blob_ship(name="Blob Ship"):
    return {"name": name, "faction": "Blob", "type": "ship"}


def _blob_world_card():
    """
    Blob World as a PRIMARY (activated) base ability:
      Activate -> Choose:
        • +5 combat
        • Draw N, where N = number of *other* Blob cards played this turn
          (i.e., count in 'played_this_turn' with faction='Blob').
    """
    return {
        "name": "Blob World",
        "faction": "Blob",
        "type": "base",
        "abilities": [
            {
                "trigger": "activated",
                "id": "blob_world_main",
                "frequency": {"once_per_turn": True},
                "effects": [
                    {
                        "type": "choose_one",
                        "options": [
                            {
                                "label": "+5 combat",
                                "effects": [{"type": "combat", "amount": 5}],
                            },
                            {
                                "label": "Draw per other Blob this turn",
                                "effects": [
                                    {
                                        "type": "count",
                                        "where": "played_this_turn",
                                        "filter": {"faction": "Blob"},
                                        "store_as": "blob_n",
                                    },
                                    {"type": "draw_from", "key": "blob_n"},
                                ],
                            },
                        ],
                    }
                ],
            }
        ],
    }


def test_blob_world_primary_choose_combat_plus_five():
    """
    Activating Blob World and choosing the first option yields +5 combat.
    """
    player = "P1"
    game, ui, api, disp = _make_env(pick_index=0)  # choose "+5 combat"

    # Put Blob World in play
    z = game.zones.setdefault(player, {})
    z["in_play"] = [ _blob_world_card() ]

    card = z["in_play"][0]
    disp.activate_card(player, card, ability_id="blob_world_main")

    assert game.combat.get(player, 0) == 5


def test_blob_world_primary_choose_draw_counts_other_blob_plays_this_turn():
    """
    Activating Blob World and choosing draw should draw as many cards as the number
    of OTHER Blob cards played this turn. We simulate two Blob ships already played.
    """
    player = "P1"
    game, ui, api, disp = _make_env(pick_index=1)  # choose the draw option

    z = game.zones.setdefault(player, {})
    # Simulate earlier plays this turn: two Blob ships
    z["played_this_turn"] = [ _blob_ship("Blob 1"), _blob_ship("Blob 2") ]
    # Blob World is just sitting in play (itself is not counted because we only count 'played_this_turn')
    z["in_play"] = [ _blob_world_card() ]

    card = z["in_play"][0]
    disp.activate_card(player, card, ability_id="blob_world_main")

    assert game.draws.get(player, 0) == 2