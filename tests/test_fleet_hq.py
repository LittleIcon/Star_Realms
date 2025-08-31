# tests/test_fleet_hq.py
from starrealms.engine.unified_dispatcher import GameAPI, AbilityDispatcher


class _FakeGame:
    def __init__(self):
        self.combat = {}
        self.zones = {}

    def add_combat(self, player, amount):
        self.combat[player] = self.combat.get(player, 0) + amount

    def add_trade(self, *a, **k): pass
    def add_authority(self, *a, **k): pass
    def draw(self, *a, **k): pass
    def force_discard(self, *a, **k): pass
    def scrap_card(self, *a, **k): pass
    def trade_row_filtered(self, *a, **k): return []
    def cost_of_trade_row(self, *a, **k): return 0
    def spend_trade(self, *a, **k): pass
    def acquire_from_trade_row(self, *a, **k): pass
    def destroy_trade_row(self, *a, **k): pass
    def destroy_enemy_base(self, *a, **k): pass
    def list_zone(self, player, zone):
        return self.zones.setdefault(player, {}).setdefault(zone, [])


class _FakeUI:
    def notify(self, msg): pass


def _make_env():
    game = _FakeGame()
    ui = _FakeUI()
    api = GameAPI(game, ui)
    disp = AbilityDispatcher(api)
    return game, ui, api, disp


def _fleet_hq():
    return {
        "name": "Fleet HQ",
        "faction": "Star Empire",
        "type": "base",
        "abilities": [
            {
                "trigger": "continuous:on_ship_played",
                "effects": [ {"type": "combat", "amount": 1} ]
            }
        ]
    }


def _scout():
    return {"name": "Scout", "faction": "Neutral", "type": "ship"}


def test_fleet_hq_gives_plus_one_combat_for_each_ship_played():
    player = "P1"
    game, ui, api, disp = _make_env()

    # Put Fleet HQ in play
    z = game.zones.setdefault(player, {})
    z["in_play"] = [ _fleet_hq() ]
    disp.on_card_enter_play(player, z["in_play"][0])

    # Play two ships
    disp.on_ship_played(player, _scout())
    disp.on_ship_played(player, _scout())

    # Expect +2 combat (1 per ship)
    assert game.combat.get(player, 0) == 2


def test_fleet_hq_does_not_apply_when_not_in_play():
    player = "P1"
    game, ui, api, disp = _make_env()

    # No Fleet HQ in play
    disp.on_ship_played(player, _scout())
    assert game.combat.get(player, 0) == 0