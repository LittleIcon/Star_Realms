# tests/test_turn_start_passive.py
from starrealms.game import Game

def test_on_turn_start_effect_triggers():
    g = Game(("Player 1","Player 2"))
    p = g.current_player()

    base = {
        "id": 9003, "name": "Ping Station", "type": "base", "faction": "Neutral",
        "abilities": [
            {"trigger": "on_turn_start", "effects": [{"type": "trade", "amount": 2}]}
        ]
    }
    p.bases.append(base)
    g.dispatcher.on_card_enter_play(p.name, base)

    before = p.trade_pool

    # Rotate: P1 end -> start P2 -> end -> start P1 (effect should fire now)
    g.end_turn()
    g.start_turn()
    g.end_turn()
    g.start_turn()

    assert p.trade_pool == before + 2