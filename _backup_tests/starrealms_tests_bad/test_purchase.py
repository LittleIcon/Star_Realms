import pytest

def test_buy_explorer_goes_to_discard(game, p1):
    # find a safe baseline
    start_discard = len(p1.discard_pile)
    # give enough trade so the buy path is valid
    p1.trade_pool = 10

    # call the public API
    game.buy_explorer(p1)

    # explorer added to discard, cost paid
    assert p1.trade_pool == 8
    assert len(p1.discard_pile) == start_discard + 1
    assert p1.discard_pile[-1]["name"].lower() == "explorer"

@pytest.mark.xfail(reason="Topdeck flag not implemented yet")
def test_buy_respects_topdeck_next_purchase_flag(game, p1):
    p1.trade_pool = 10
    # simulate effect setting the flag
    p1.topdeck_next_purchase = True

    start_deck = len(p1.deck)
    start_discard = len(p1.discard_pile)

    game.buy_explorer(p1)

    # once implemented, Explorer should be placed on top of deck, not discard
    assert len(p1.deck) == start_deck + 1
    assert len(p1.discard_pile) == start_discard
    assert p1.deck[-1]["name"].lower() == "explorer"
    # flag should auto-clear after use
    assert not getattr(p1, "topdeck_next_purchase", False)