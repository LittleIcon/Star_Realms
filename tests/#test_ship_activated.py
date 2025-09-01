#test_ship_activated.py

import pytest

from starrealms.game import Game
from starrealms.ui import use_action

def setup_game_nonhuman_actor():
    """Return (g, p, o) with p = non-human Player 2."""
    g = Game(("Player 1", "Player 2"))
    p = g.players[1]  # non-human by default
    o = g.players[0]
    return g, p, o

def _explorer_like_scrap_ship():
    """
    Minimal ship with a scrap effect using the NEW schema:
      trigger: "scrap_activated" -> +2 combat
    """
    return {
        "name": "Test Explorer",
        "type": "ship",
        "faction": "Neutral",
        "cost": 2,
        "abilities": [
            {
                "id": "TestExplorer_scrap",
                "trigger": "scrap_activated",
                "effects": [{"type": "combat", "amount": 2}],
            }
        ],
        # No legacy "scrap" block on purpose—this test verifies the abilities bridge works.
    }

def test_ship_with_scrap_activated_engine_path():
    """
    Engine path: Player.activate_ship(card, scrap=True) should:
      - apply the scrap effect (+2 combat)
      - remove the ship from in_play
      - move the ship to the scrap heap
    """
    g, p, o = setup_game_nonhuman_actor()
    ship = _explorer_like_scrap_ship()

    # Put ship into play directly (simulates having played it earlier this turn)
    p.in_play.append(ship)
    start_combat = p.combat_pool

    ok = p.activate_ship(ship, o, g, scrap=True)
    assert ok is True
    assert p.combat_pool == start_combat + 2
    assert ship not in p.in_play
    # Either player or game scrap heap is acceptable depending on engine; check both.
    in_player_heap = hasattr(p, "scrap_heap") and ship in p.scrap_heap
    in_game_heap = hasattr(g, "scrap_heap") and ship in g.scrap_heap
    assert in_player_heap or in_game_heap

def test_ship_with_scrap_activated_ui_path(monkeypatch):
    """
    UI path: use_action() should list the ship as scrappable, let the user confirm,
    apply effect, and remove it from play.
    """
    g, p, o = setup_game_nonhuman_actor()
    ship = _explorer_like_scrap_ship()
    p.in_play.append(ship)
    start_combat = p.combat_pool

    # Sequence:
    #  - "1" to pick the first (and only) scrappable entry
    #  - "y" to confirm scrapping the ship
    inputs = iter(["1", "y"])

    # Silence UI printing during the test
    from starrealms.view import ui_common
    monkeypatch.setattr(ui_common, "ui_input", lambda prompt="": next(inputs))
    monkeypatch.setattr(ui_common, "ui_print", lambda *a, **k: None)
    # (We don’t need ui_log, but patching is harmless)
    if hasattr(ui_common, "ui_log"):
        monkeypatch.setattr(ui_common, "ui_log", lambda *a, **k: None)

    # Invoke the UI “Use (base/ship)” flow
    use_action(p, o, g)

    # Assert the scrap happened
    assert p.combat_pool == start_combat + 2
    assert ship not in p.in_play
    in_player_heap = hasattr(p, "scrap_heap") and ship in p.scrap_heap
    in_game_heap = hasattr(g, "scrap_heap") and ship in g.scrap_heap
    assert in_player_heap or in_game_heap