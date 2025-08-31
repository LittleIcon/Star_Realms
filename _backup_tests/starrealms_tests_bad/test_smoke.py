def test_game_starts_with_expected_hands(game, p1, p2):
    # your Game() deals P1:3, P2:5 on init
    assert len(p1.hand) == 3
    assert len(p2.hand) == 5
    # trade row has 5 slots
    assert len(game.trade_row) == 5