# tests/test_missile_mech_ally_draw_one.py

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

    # Deterministic deck for draw checks
    p1.deck[:] = [{"name": "Card A"}, {"name": "Card B"}, {"name": "Card C"}]

    # Satisfy ally WITHOUT adding extra combat: a no-op MC ship already in play
    p1.in_play.append({"name": "MC Helper", "faction": "Machine Cult", "type": "ship"})

    # Put Missile Mech in hand
    missile_mech = get_card_by_name(g.trade_deck + g.card_db, "Missile Mech")
    assert missile_mech
    p1.hand.append(missile_mech)

    start_hand = len(p1.hand)
    start_deck = len(p1.deck)
    start_combat = p1.combat_pool

    # Play Missile Mech
    assert p1.play_card(missile_mech, p2, g) is True

    # On-play: +6 combat only
    assert p1.combat_pool == start_combat + 6

    # Ally: draw exactly 1 card (net hand +0 vs. pre-play, but +1 vs. immediate post-play baseline)
    assert len(p1.hand) == start_hand  # played one, drew one → net zero vs. baseline taken before play
    assert len(p1.deck) == start_deck - 1

    # Log checks: no "draws 2", and the draw log follows the ally trigger log
    log = getattr(g, "log", [])
    assert not any("draws 2 card(s)" in line for line in log), "Missile Mech should not draw 2 on ally."

    ally_idx = _find_index(log, r"(triggers|triggered).*(Missile Mech).*ally")
    assert ally_idx >= 0, "Could not find ally trigger log for Missile Mech."
    assert ally_idx + 1 < len(log), "No log line after the ally trigger message."
    assert re.search(r"draws 1 card\(s\)", log[ally_idx + 1]), (
        "Ally effect log should immediately follow ally trigger log "
        f"(got: {log[ally_idx]!r} -> {log[ally_idx+1]!r})"
    )