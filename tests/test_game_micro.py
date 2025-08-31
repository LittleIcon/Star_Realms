# tests/test_game_micro.py
from starrealms.game import Game

def test_buy_explorer_and_topdeck_flag():
    g = Game(("P1", "P2"))
    p = g.current_player()

    # Give player enough trade
    p.trade_pool = 5
    # Case 1: normal buy → goes to discard
    g.buy_explorer(p)
    assert any(c["name"] == "Explorer" for c in p.discard_pile)
    assert "buys Explorer" in g.log[-1]

    # Case 2: topdeck flag → goes to deck front
    p.trade_pool = 5
    p.topdeck_next_purchase = True
    g.buy_explorer(p)
    assert p.deck[0]["name"] == "Explorer"
    assert "top-deck" in g.log[-2] or "top-deck" in g.log[-1]

def test_destroy_trade_row_and_record_played():
    g = Game(("P1", "P2"))
    p = g.current_player()

    # Save a card name from row
    first_name = g.trade_row[0]["name"]

    g.destroy_trade_row(0)
    # It should end up in scrap_heap
    assert any(c["name"] == first_name for c in g.scrap_heap)

    # Test record_played_this_turn
    fake_card = {"name": "Fake Ship"}
    g.record_played_this_turn(p.name, fake_card)
    assert fake_card in g._played_this_turn[p.name]