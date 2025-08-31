# starrealms/tests/test_player_buy_and_topdeck.py

from starrealms.game import Game

def test_buy_card_to_discard_vs_topdeck():
    g = Game(("P1", "P2"))
    p = g.current_player()

    # Ensure there is a card to buy
    assert g.trade_row[0] is not None
    card0 = g.trade_row[0]

    # Buy normally → goes to discard
    p.trade_pool = 50  # enough to buy anything
    assert p.buy_card(card0, g) is True
    assert any(c["name"] == card0["name"] for c in p.discard_pile)

    # Put another known card in slot 0 to buy again
    assert g.trade_row[0] is not None
    card1 = g.trade_row[0]

    # Top-deck next purchase → goes to top of deck
    p.topdeck_next_purchase = True
    p.trade_pool = 50
    assert p.buy_card(card1, g) is True
    assert p.deck and p.deck[0]["name"] == card1["name"]