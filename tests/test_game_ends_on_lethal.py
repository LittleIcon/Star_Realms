# tests/test_game_ends_on_lethal.py
# Verifies the game immediately ends (and winner recorded) when a player’s
# authority hits 0 or below from combat.

import pytest
from starrealms.game import Game

def _give_lethal_combat(p, amount):
    # helper: push combat into the pool so your normal damage path can spend it
    p.combat_pool += amount

def _spend_combat_to_face(g, attacker, defender, amount):
    g.spend_combat_to_face(attacker, defender, amount)

def test_game_ends_at_exact_zero():
    g = Game(("P1", "P2"))
    p1, p2 = g.players

    p2.authority = 5
    _give_lethal_combat(p1, 5)
    _spend_combat_to_face(g, p1, p2, 5)

    # Expect immediate end & winner recorded
    assert getattr(g, "over", False) or getattr(g, "is_over", False), "Game should be marked over"
    assert getattr(g, "winner", None) in (p1.name, "P1"), "Winner should be the attacker"
    # (Optional) a log line if your engine logs it
    assert any("wins" in s.lower() or "game over" in s.lower() for s in getattr(g, "log", [])), \
        "Should log a clear end-of-game message"


def test_game_ends_below_zero():
    g = Game(("P1", "P2"))
    p1, p2 = g.players

    p2.authority = 3
    _give_lethal_combat(p1, 10)
    _spend_combat_to_face(g, p1, p2, 10)

    assert getattr(g, "over", False) or getattr(g, "is_over", False), "Game should be marked over"
    assert getattr(g, "winner", None) in (p1.name, "P1")