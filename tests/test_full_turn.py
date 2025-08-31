from starrealms.runner.controller import apply_command

def _ship(name, on_play_effects):
    return {
        "name": name,
        "type": "ship",
        "on_play": list(on_play_effects),  # e.g., [{"type":"trade","amount":3}]
    }

def test_full_turn_play_buy_attack_end(game):
    p1, p2 = game.players[0], game.players[1]

    # Start the turn explicitly (your loop does this outside the controller)
    game.start_turn()

    # Deterministic hand: +3 trade, +5 combat on play
    p1.hand[:] = [
        _ship("Cargo Sloop",   [{"type": "trade",  "amount": 3}]),
        _ship("War Cutter",    [{"type": "combat", "amount": 5}]),
    ]
    p1.in_play.clear()
    p1.discard_pile.clear()

    # 1) PLAY ALL
    last_log = 0
    last_log = apply_command(game, "pa", None, last_log, echo=False)
    assert p1.trade_pool == 3
    assert p1.combat_pool == 5
    assert len(p1.hand) == 0
    assert len(p1.in_play) == 2

    # 2) BUY EXPLORER (cost 2)
    last_log = apply_command(game, "b", "x", last_log, echo=False)
    assert p1.trade_pool == 1  # 3 - 2
    # Explorer should go to discard unless a topdeck flag was set (we didn't set it)
    assert any(c["name"].lower() == "explorer" for c in p1.discard_pile)

    # 3) ATTACK (AI path auto-resolves since P1 is not human)
    last_log = apply_command(game, "a", None, last_log, echo=False)
    assert p1.combat_pool == 0
    # Took 5 authority from opponent (no outposts were present)
    assert p2.authority == 50 - 5

    # 4) END TURN (cleanup, draw 5, pass turn)
    last_log = apply_command(game, "e", None, last_log, echo=False)
    # In-play moved to discard; drew a fresh 5-card hand
    assert len(p1.in_play) == 0
    assert len(p1.hand) == 5
    # Turn passed to P2
    assert game.current_player() is p2
