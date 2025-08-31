from starrealms.runner.controller import apply_command

def _ship(name, faction, on_play=None, ally=None):
    return {
        "name": name,
        "type": "ship",
        "faction": faction,
        "on_play": list(on_play or []),
        "ally":   list(ally or []),
    }

def test_full_turn_with_ally_triggers_once(game):
    p1, p2 = game.players[0], game.players[1]
    game.start_turn()

    # First ship has an ALLY ability (+3 combat). Second ship shares the same faction.
    s1 = _ship("Ally Ship A", "Blob", on_play=[], ally=[{"type": "combat", "amount": 3}])
    s2 = _ship("Trade Buddy", "Blob", on_play=[{"type": "trade", "amount": 2}])

    # Force a deterministic hand (exactly these two)
    p1.hand[:] = [s1, s2]
    p1.in_play.clear()
    p1.discard_pile.clear()

    # PLAY ALL -> s2 gives +2 trade; ally on s1 should trigger once for +3 combat
    last = 0
    last = apply_command(game, "pa", None, last, echo=False)
    assert p1.trade_pool == 2
    assert p1.combat_pool == 3

    # Re-running ally resolution should NOT stack further
    again_trade = p1.trade_pool
    again_combat = p1.combat_pool
    game.resolve_allies(p1)
    assert p1.trade_pool == again_trade
    assert p1.combat_pool == again_combat

    # Buy Explorer (cost 2), attack, end turn to complete the loop
    last = apply_command(game, "b", "x", last, echo=False)
    assert p1.trade_pool == 0
    last = apply_command(game, "a", None, last, echo=False)
    assert p1.combat_pool == 0
    assert p2.authority == 50 - 3  # took the ally combat to the face
    last = apply_command(game, "e", None, last, echo=False)

    # End-of-turn cleanup: new hand of 5, in_play cleared, turn passed
    assert len(p1.in_play) == 0
    assert len(p1.hand) == 5
    assert game.current_player() is p2
