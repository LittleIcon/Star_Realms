# tests/test_missile_mech_ally_draw_one.py
# file: tests/test_missile_mech_ally_draw_one.py

import re
from starrealms.game import Game
from starrealms.cards import get_card_by_name

def _find_index(lines, pattern):
    rx = re.compile(pattern)
    for i, line in enumerate(lines):
        if rx.search(line):
            return i
    return -1

def test_missile_mech_ally_draws_exactly_one_card():
    """
    Missile Mech ally should draw exactly 1 card (not 2).
    Also verify the ally-trigger log is immediately followed by the draw log.
    """
    g = Game(("P1", "P2"))
    p1, p2 = g.current_player(), g.opponent()

    # Ensure we have deterministic cards to draw
    p1.deck[:] = [{"name": "Card A"}, {"name": "Card B"}, {"name": "Card C"}]

    # Satisfy ally condition: play another Machine Cult card first (e.g., Trade Bot)
    trade_bot = get_card_by_name(g.trade_deck + g.card_db, "Trade Bot")
    missile_mech = get_card_by_name(g.trade_deck + g.card_db, "Missile Mech")
    assert trade_bot and missile_mech

    p1.hand.extend([trade_bot, missile_mech])

    # Play MC helper then Missile Mech
    assert p1.play_card(trade_bot, p2, g) is True

    start_hand = len(p1.hand)
    start_deck = len(p1.deck)
    start_combat = p1.combat_pool

    assert p1.play_card(missile_mech, p2, g) is True

    # On-play combat +6 happened
    assert p1.combat_pool == start_combat + 6

    # Ally draw: exactly one card drawn
    assert len(p1.hand) == start_hand + 1
    assert len(p1.deck) == start_deck - 1

    log = getattr(g, "log", [])

    # There must NOT be a "draws 2" anywhere
    assert not any("draws 2 card(s)" in line for line in log), "Missile Mech should not draw 2 on ally."

    # Ally trigger line must be present, and the very next line must be the single-card draw
    ally_idx = _find_index(log, r"(triggers|triggered).*(Missile Mech).*ally")
    assert ally_idx >= 0, "Could not find ally trigger log for Missile Mech."
    assert ally_idx + 1 < len(log), "No log line after the ally trigger message."
    assert re.search(r"draws 1 card\(s\)", log[ally_idx + 1]), (
        "Ally effect log should immediately follow ally trigger log "
        f"(got: {log[ally_idx]!r} -> {log[ally_idx+1]!r})"
    )