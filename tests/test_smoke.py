def test_game_starts_with_expected_hands(game, p1, p2):
    assert len(p1.hand) == 3
    assert len(p2.hand) == 5
    assert len(game.trade_row) == 5
