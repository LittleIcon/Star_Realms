# tests/test_human_opponent_discard_choice.py
# file: tests/test_human_opponent_discard_choice.py

import re
from starrealms.game import Game
from starrealms.cards import get_card_by_name
from starrealms.view import ui_common

def test_human_opponent_chooses_discard(monkeypatch):
    """
    When an ally effect makes the opponent discard, and that opponent is human,
    they should be prompted to choose the card to discard (not the AI auto path).

    Scenario:
      - P1 plays Royal Redoubt (Star Empire).
      - We ensure ally condition is satisfied.
      - P2 is human and has a hand with known cards.
      - The prompt appears and P2 selects "Viper" by index.
      - The engine discards *that* chosen card and logs accordingly.
    """
    g = Game(("P1", "P2"))
    p1, p2 = g.current_player(), g.opponent()

    # Make opponent human (this is the crucial part that should take the human path)
    p2.human = True

    # Ensure ally condition for Royal Redoubt is met.
    # Easiest: put a same-faction (Star Empire) card already in P1's in_play.
    p1.in_play.append({"name": "SE Helper", "faction": "Star Empire", "type": "ship"})

    # Give P2 a known hand we can select from
    scout   = {"name": "Scout"}
    explorer= {"name": "Explorer"}
    viper   = {"name": "Viper"}
    p2.hand[:] = [scout, explorer, viper]

    # Fetch Royal Redoubt from the card DB
    royal_redoubt = get_card_by_name(g.trade_deck + g.card_db, "Royal Redoubt")

    # Monkeypatch UI so the human selects index "3" (Viper) when asked
    inputs = iter(["3"])
    monkeypatch.setattr(ui_common, "ui_input", lambda prompt="": next(inputs))
    # (Printing isn't required, but stub it so printing won't crash if referenced)
    monkeypatch.setattr(ui_common, "ui_print", lambda *a, **k: None)

    # Play the base; this should trigger ally -> human discard prompt
    assert p1.play_card(royal_redoubt, p2, g) is True

    # Verify the chosen card (Viper) was discarded — not the first/auto card.
    assert viper in p2.discard_pile, "Human-selected card was not discarded"
    assert viper not in p2.hand, "Viper should be removed from hand after discard"
    # Sanity: ensure others stayed
    assert scout in p2.hand and explorer in p2.hand

    # Logs should show ally trigger, then the discard
    log = getattr(g, "log", [])
    ally_idx = next((i for i, line in enumerate(log)
                     if re.search(r"triggers .*Royal Redoubt.* ally", line)), -1)
    assert ally_idx >= 0, "Missing ally trigger log for Royal Redoubt"

    # After the trigger, we expect a discard line mentioning Viper
    after = "\n".join(log[ally_idx:ally_idx+4])  # small window
    assert any("discards Viper" in line for line in log[ally_idx:ally_idx+4]), (
        "Expected the human discard of 'Viper' immediately after ally trigger.\n"
        f"Nearby log lines:\n{after}"
    )