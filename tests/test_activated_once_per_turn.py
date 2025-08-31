# tests/test_activated_once_per_turn.py
from starrealms.game import Game

def test_activated_once_per_turn_respects_guard():
    g = Game(("Player 1","Player 2"))
    p = g.current_player(); o = g.opponent()

    base = {
        "id": 9004, "name": "Tapper", "type": "base", "faction": "Neutral",
        "abilities": [
            {"id": "tap1", "trigger": "activated", "frequency": {"once_per_turn": True},
             "effects": [{"type":"combat","amount":3}]}
        ]
    }
    p.bases.append(base)
    g.dispatcher.on_card_enter_play(p.name, base)

    # First activation grants +3
    g.dispatcher.activate_card(p.name, base, ability_id="tap1")
    c1 = p.combat_pool
    # Second activation same turn should do nothing
    g.dispatcher.activate_card(p.name, base, ability_id="tap1")
    c2 = p.combat_pool
    assert c1 == 3 and c2 == 3