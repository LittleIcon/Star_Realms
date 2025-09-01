# tests/test_royal_redoubt_no_manual_activate.py
# file: tests/test_royal_redoubt_no_manual_activate.py

import re
from starrealms.game import Game
from starrealms.cards import get_card_by_name
from starrealms.view import ui_common

def test_royal_redoubt_has_no_manual_activation(monkeypatch):
    """
    Royal Redoubt has no activated ability. Its +3 combat is on-play, and the
    discard is an ally effect. Attempting to activate the base must do nothing:
      - no extra combat,
      - no extra discard,
      - no 'uses/activates Royal Redoubt' log line.
    """
    g = Game(("P1", "P2"))
    p1, p2 = g.current_player(), g.opponent()

    # Make opponent human so discard prompt path is used (deterministic)
    p2.human = True
    p2.hand[:] = [{"name": "Scout"}, {"name": "Blob Wheel"}, {"name": "Viper"}]
    monkeypatch.setattr(ui_common, "ui_input", lambda prompt="": "2")  # discard Blob Wheel
    monkeypatch.setattr(ui_common, "ui_print", lambda *a, **k: None)

    # Ensure ally condition: another Star Empire card already in play
    p1.in_play.append({"name": "SE Helper", "faction": "Star Empire", "type": "ship"})

    rr = get_card_by_name(g.trade_deck + g.card_db, "Royal Redoubt")
    assert rr and rr.get("type") == "base"

    # --- Play Royal Redoubt: on-play +3 combat; ally → opponent discards 1 ---
    start_combat = p1.combat_pool
    assert p1.play_card(rr, p2, g) is True

    # on-play combat applied once
    assert p1.combat_pool == start_combat + 3, "Royal Redoubt should give +3 combat on play."

    # ally discard applied once (the chosen 'Blob Wheel')
    assert any(c.get("name") == "Blob Wheel" for c in p2.discard_pile), \
        "Expected ally-triggered discard of 'Blob Wheel' on play."
    initial_discards = len(p2.discard_pile)

    # --- Try to activate the base: SHOULD DO NOTHING ---
    used = p1.activate_base(rr, p2, g, scrap=False)
    assert used is False, "Royal Redoubt must NOT be manually activatable."

    # No extra combat granted
    assert p1.combat_pool == start_combat + 3, \
        "Manual activation incorrectly added more combat."

    # No extra discard either
    assert len(p2.discard_pile) == initial_discards, \
        "Manual activation incorrectly caused another discard."

    # And no 'use/activate' log lines
    log = getattr(g, "log", [])
    assert not any(re.search(r"\buses Royal Redoubt\b", line) for line in log), \
        "Log should not claim Royal Redoubt was 'used'."
    assert not any(re.search(r"\bactivates Royal Redoubt\b", line) for line in log), \
        "Log should not claim Royal Redoubt was 'activated'."