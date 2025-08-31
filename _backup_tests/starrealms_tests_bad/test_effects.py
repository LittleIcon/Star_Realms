from random import Random
from starrealms.engine.state import GameState, PlayerState
from starrealms.engine.resolver import apply_effect
def test_trade_effect_adds_trade():
    s = GameState(Random(0), {"P1": PlayerState("P1"), "P2": PlayerState("P2")}, [], [])
    apply_effect(s, {"type":"trade","amount":3}, "P1")
    assert s.players["P1"].trade == 3
