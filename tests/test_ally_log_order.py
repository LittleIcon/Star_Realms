# tests/test_ally_log_order.py
import re
from starrealms.game import Game
from starrealms.cards import get_card_by_name

def _find_index(lines, pattern):
    """Return the first index of a line matching regex pattern, else -1."""
    rx = re.compile(pattern)
    for i, line in enumerate(lines):
        if rx.search(line):
            return i
    return -1

def test_trade_pod_ally_log_precedes_effect():
    """
    When an ally effect triggers, the log line announcing the ally trigger
    should print *right before* the log line for that ally effect.

    Scenario:
      - Play Blob Fighter (puts a Blob ship into play)
      - Play Trade Pod
        On-play: +3 trade
        Ally:    +2 combat (because another Blob is in play)
    """
    g = Game(("P1", "P2"))
    p1, p2 = g.current_player(), g.opponent()

    # Pull the cards from the card DB
    blob_fighter = get_card_by_name(g.trade_deck + g.card_db, "Blob Fighter")
    trade_pod    = get_card_by_name(g.trade_deck + g.card_db, "Trade Pod")

    # Put them in hand and play in order
    p1.hand.extend([blob_fighter, trade_pod])
    assert p1.play_card(blob_fighter, p2, g) is True
    assert p1.play_card(trade_pod,    p2, g) is True

    # We expect logs something like:
    #  • P1 gains +3 trade ...
    #  • P1 triggers Trade Pod ally via ally (Blob)
    #  • P1 gains +2 combat ...
    log = getattr(g, "log", [])

    # Verify on-play happened (sanity)
    assert any("gains +3 trade" in line for line in log), "Missing on-play trade log for Trade Pod"

    # Find the ally trigger line; accept a few phrasings but require the card name + 'ally'
    ally_idx = _find_index(
        log,
        r"(triggers|triggered).*(Trade Pod).*ally"
    )
    assert ally_idx >= 0, f"Could not find ally trigger log for Trade Pod.\nLog:\n" + "\n".join(log)

    # The next line must be the ally effect (+2 combat)
    effect_idx = ally_idx + 1
    assert effect_idx < len(log), "No log line after the ally trigger message"
    assert re.search(r"gains \+2 combat", log[effect_idx]), (
        "Ally effect log should immediately follow ally trigger log.\n"
        f"trigger: {log[ally_idx]!r}\n"
        f"effect?: {log[effect_idx]!r}"
    )