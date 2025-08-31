import copy
from starrealms.game import Game

def test_continuous_aura_turns_off_when_base_leaves():
    # Fresh game
    g = Game(("Player 1", "Player 2"))
    p = g.current_player()
    o = g.opponent()

    # Add a base with a continuous aura: +1 combat whenever a ship is played
    aura_base = {
        "id": 9001,
        "name": "Test Aura Base",
        "type": "base",
        "faction": "Star Empire",
        "defense": 5,
        "outpost": False,
        "abilities": [
            {
                "id": "aura1",
                "trigger": "continuous:on_ship_played",
                "effects": [ { "type": "combat", "amount": 1 } ]
            }
        ]
    }

    # Put base into play and notify dispatcher
    p.bases.append(aura_base)
    g.dispatcher.on_card_enter_play(p.name, aura_base)

    # Create a dummy ship that does NOT add its own combat,
    # so we can isolate the aura (+1) precisely.
    dummy_ship = {
        "id": 9002,
        "name": "Dummy Ship",
        "type": "ship",
        "faction": "Neutral",
        "on_play": [ { "type": "combat", "amount": 0 } ],
    }

    # 1) Aura should fire on ship play (+1 combat)
    p.hand.append(copy.deepcopy(dummy_ship))
    before = p.combat_pool
    p.play_card(p.hand[-1], o, g)
    after = p.combat_pool
    assert (after - before) == 1, f"Aura should add +1 combat; got delta {after - before}"

    # 2) Simulate base leaving play -> aura unregistered
    g.dispatcher.on_card_leave_play(p.name, aura_base)

    # Play another dummy ship; aura should NOT add further combat
    p.hand.append(copy.deepcopy(dummy_ship))
    before2 = p.combat_pool
    p.play_card(p.hand[-1], o, g)
    after2 = p.combat_pool
    assert (after2 - before2) == 0, f"Aura should be off; expected delta 0, got {after2 - before2}"