# starrealms/tests/test_player_end_turn_cleanup.py

from starrealms.game import Game

def _mk(name): return {"name": name, "type": "ship"}

def test_end_turn_moves_hand_and_inplay_and_draws():
    g = Game(("P1","P2"))
    p = g.current_player()

    # Give a small, controlled deck so we can predict draw count
    p.deck[:] = [{"name": f"D{i}", "type": "ship"} for i in range(10)]
    p.hand[:] = [_mk("H1"), _mk("H2")]
    p.in_play[:] = [_mk("S1")]
    p.bases[:] = [{"name": "B1", "type": "base", "defense": 3, "outpost": False, "_used": True}]

    # Buff pools/flags to ensure they reset
    p.trade_pool = 5
    p.combat_pool = 7
    p.per_ship_combat_bonus = 2
    p.topdeck_next_purchase = True  # persists across turns

    p.end_turn()

    # Hand + in_play moved to discard
    names = [c["name"] for c in p.discard_pile]
    assert "H1" in names and "H2" in names and "S1" in names

    # Bases remain and have _used reset
    assert p.bases and p.bases[0].get("_used") is False

    # Pools reset; per_turn bonus reset
    assert p.trade_pool == 0 and p.combat_pool == 0
    assert p.per_ship_combat_bonus == 0

    # Drew 5 new cards
    assert len(p.hand) == 5