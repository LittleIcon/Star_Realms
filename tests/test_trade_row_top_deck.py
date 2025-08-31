def test_trade_row_buy_respects_topdeck_flag(game, p1):
    # arrange: make sure there is a card and enough trade
    assert game.trade_row[0] is not None
    p1.trade_pool = 20
    p1.topdeck_next_purchase = True
    start_deck = len(p1.deck)
    start_discard = len(p1.discard_pile)

    # simulate buying slot 0 like your controller would
    card = game.trade_row[0]
    game.trade_row[0] = None
    # this is what controller.py should call:
    game._acquire(p1, card)
    game.refill_trade_row()

    assert len(p1.deck) == start_deck + 1
    assert len(p1.discard_pile) == start_discard
    assert p1.deck[0]["name"] == card["name"]
    assert not getattr(p1, "topdeck_next_purchase", False)