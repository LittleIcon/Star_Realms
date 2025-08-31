import pytest

def test_buy_explorer_goes_to_discard(game, p1):
    start_discard = len(p1.discard_pile)
    p1.trade_pool = 10
    game.buy_explorer(p1)
    assert p1.trade_pool == 8
    assert len(p1.discard_pile) == start_discard + 1
    assert p1.discard_pile[-1]["name"].lower() == "explorer"

def test_buy_respects_topdeck_next_purchase_flag(game, p1):
    p1.trade_pool = 10
    p1.topdeck_next_purchase = True
    start_deck = len(p1.deck)
    start_discard = len(p1.discard_pile)
    game.buy_explorer(p1)
    assert len(p1.deck) == start_deck + 1
    assert len(p1.discard_pile) == start_discard
    assert p1.deck[0]["name"].lower() == "explorer"
    assert not getattr(p1, "topdeck_next_purchase", False)
