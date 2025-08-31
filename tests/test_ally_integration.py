# tests/test_ally_integration.py
import pytest

from starrealms.engine.unified_dispatcher import GameAPI, AbilityDispatcher


# ---- Minimal fake Game + UI harness (matches patterns used elsewhere) ----
class _FakeGame:
    def __init__(self):
        self.trade = {}
        self.combat = {}
        self.authority = {}
        self.draws = {}
        self.zones = {}  # zones[player][zone] -> list[card]

    def _inc(self, d, k, v=1):
        d[k] = d.get(k, 0) + v

    def add_trade(self, p, amt):     self._inc(self.trade, p, amt)
    def add_combat(self, p, amt):    self._inc(self.combat, p, amt)
    def add_authority(self, p, amt): self._inc(self.authority, p, amt)
    def draw(self, p):               self._inc(self.draws, p, 1)

    def force_discard(self, target, n=1):
        hand = self.zones.setdefault(target, {}).setdefault("hand", [])
        for _ in range(n):
            if hand: hand.pop(0)

    def list_zone(self, player, zone):
        return self.zones.setdefault(player, {}).setdefault(zone, [])

    # (market / other ops not needed for these tests)


class _FakeUI:
    def notify(self, msg):  # collect if you want; not used here
        pass


def _make_env():
    game = _FakeGame()
    ui = _FakeUI()
    api = GameAPI(game, ui)
    disp = AbilityDispatcher(api)
    return game, ui, api, disp


# ---------------------------------------------------------------------------
# 1) Integration test with the "real" Federation Shuttle JSON encoding
#    (second ability is on_play gated by faction_in_play: this_turn).
#    Desired game behavior: both shuttles give +4 authority (= +8 total) when
#    the second enters play. Current engine only applies the second card’s
#    gated on_play, so this is marked xfail until retro-triggering or true
#    'ally' triggers are implemented for the first card.
# ---------------------------------------------------------------------------
@pytest.mark.xfail(reason="Retro-triggering of conditional on_play ally not implemented; expect +8 once added.")
def test_integration_two_federation_shuttles_real_json():
    game, ui, api, disp = _make_env()
    player = "P1"

    def shuttle_card():
        return {
            "schema_version": 2,
            "name": "Federation Shuttle",
            "faction": "Trade Federation",
            "type": "ship",
            "abilities": [
                # on_play: +2 trade
                {"trigger": "on_play", "effects": [{"type": "trade", "amount": 2}]},
                # ally encoded as conditional on_play (as in real JSON)
                {
                    "trigger": "on_play",
                    "condition": {
                        "faction_in_play": {
                            "faction": "Trade Federation",
                            "min": 1,
                            "scope": "this_turn",
                        }
                    },
                    "effects": [{"type": "authority", "amount": 4}],
                },
            ],
        }

    s1 = shuttle_card()
    s2 = shuttle_card()

    # First enters play: only one TF so far => no ally (+4) yet.
    game.zones.setdefault(player, {})["in_play"] = [s1]
    disp.on_card_enter_play(player, s1)
    assert game.authority.get(player, 0) == 0

    # Second enters play: desired behavior is that BOTH ally effects apply (+8).
    game.zones[player]["in_play"].append(s2)
    disp.on_card_enter_play(player, s2)
    assert game.authority.get(player, 0) == 8  # xfail until supported


# ---------------------------------------------------------------------------
# 2) Mech World / ally_any_faction support
#    Desired: Mech World counts as all factions while in play; playing a single
#    Federation Shuttle should then satisfy its ally and grant +4 authority.
#    Marked xfail until ally_any_faction is wired into the dispatcher/API.
# ---------------------------------------------------------------------------
@pytest.mark.xfail(reason="ally_any_faction flag is not yet wired into faction_in_play checks.")
def test_mech_world_enables_shuttle_ally():
    game, ui, api, disp = _make_env()
    player = "P1"

    mech_world = {
        "name": "Mech World",
        "faction": "Machine Cult",
        "type": "base",
        "abilities": [
            {"trigger": "on_play", "effects": [{"type": "ally_any_faction"}]}
        ],
    }

    federation_shuttle = {
        "name": "Federation Shuttle",
        "faction": "Trade Federation",
        "type": "ship",
        "abilities": [
            {"trigger": "on_play", "effects": [{"type": "trade", "amount": 2}]},
            # ally as a real ally trigger (or conditional on_play; either should work once ally_any_faction is live)
            {"trigger": "ally", "faction": "Trade Federation",
             "effects": [{"type": "authority", "amount": 4}]},
        ],
    }

    # Put Mech World into play, then play a single Shuttle.
    game.zones.setdefault(player, {})["in_play"] = [mech_world]
    disp.on_card_enter_play(player, mech_world)

    game.zones[player]["in_play"].append(federation_shuttle)
    disp.on_card_enter_play(player, federation_shuttle)

    # With ally-any-faction active, Shuttle should get its +4 ally.
    assert game.authority.get(player, 0) == 4  # xfail until supported