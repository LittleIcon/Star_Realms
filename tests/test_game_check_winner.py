# starrealms/tests/test_game_check_winner.py

from starrealms.game import Game

def test_check_winner_current_or_opponent():
    g = Game(("P1","P2"))
    p = g.current_player()
    o = g.opponent()

    # If opponent reaches 0, current player wins
    o.authority = 0
    w = g.check_winner()
    assert w is p

    # Reset and make current player reach 0; then opponent should win
    o.authority = 50
    p.authority = -1
    w2 = g.check_winner()
    assert w2 is o