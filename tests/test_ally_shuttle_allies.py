# tests/test_ally_shuttle_allies.py
import pytest
from starrealms.engine.unified_dispatcher import GameAPI, AbilityDispatcher

# --- Minimal fakes (only what the dispatcher touches here) ---

class _FakeGame:
    def __init__(self):
        self.authority = {}
        self.trade = {}
        self.zones = {}  # zones[player][zone] -> list of cards
        self.recorded = []

    def add_authority(self, player, amount):
        self.authority[player] = self.authority.get(player, 0) + int(amount)

    def add_trade(self, player, amount):
        self.trade[player] = self.trade.get(player, 0) + int(amount)

    def draw(self, player):  # not used in this test
        pass

    def list_zone(self, player, zone):
        return self.zones.setdefault(player, {}).setdefault(zone, [])

    def record_played_this_turn(self, player, card):
        self.recorded.append((player, card))


class _FakeUI:
    def __init__(self):
        self.notifications = []

    def notify(self, msg):
        self.notifications.append(msg)


def _make_env():
    game = _FakeGame()
    ui = _FakeUI()
    api = GameAPI(game, ui)
    disp = AbilityDispatcher(api)
    return game, ui, api, disp


def test_both_federation_shuttle_allies_trigger():
    """
    When two Trade Federation ships with 'ally' abilities are in play,
    both ally abilities should fire once the second ship enters play.
    Expected: +8 authority total from two allies (+4 each).
    """
    game, ui, api, disp = _make_env()
    player = "P1"

    # Federation Shuttle model:
    # - on_play: trade +2
    # - ally (TF): authority +4
    def shuttle(name):
        return {
            "name": name,
            "faction": "Trade Federation",
            "abilities": [
                {"trigger": "on_play", "effects": [{"type": "trade", "amount": 2}]},
                # Allow either ally encoding; the dispatcher supports both.
                {"trigger": "ally", "faction": "Trade Federation",
                 "effects": [{"type": "authority", "amount": 4}]},
            ],
        }

    s1 = shuttle("Federation Shuttle")
    s2 = shuttle("Federation Shuttle")

    # Put the first shuttle into in_play and notify dispatcher.
    game.zones.setdefault(player, {})["in_play"] = [s1]
    disp.on_card_enter_play(player, s1)

    # At this point only one TF is in play → no ally yet
    assert game.authority.get(player, 0) == 0

    # Now play the second shuttle: add to in_play, then notify dispatcher.
    game.zones[player]["in_play"].append(s2)
    disp.on_card_enter_play(player, s2)

    # After the second TF appears, dispatcher should re-evaluate allies and
    # fire ally on BOTH shuttles exactly once: +4 +4 = +8 authority.
    assert game.authority.get(player, 0) == 8

    # (Optional) sanity: trade from on_play happened twice (+2 each)
    assert game.trade.get(player, 0) == 4