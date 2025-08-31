#test/test_mini_game_ops.py
from starrealms.game import Game
from starrealms.cards import EXPLORER_NAME

def test_buy_explorer_adds_to_discard_and_logs():
    g = Game(("you", "cpu"))
    p = g.current_player()
    p.trade_pool = 2
    g.buy_explorer(p)
    assert any(c["name"] == EXPLORER_NAME for c in p.discard_pile)
    assert any("buys Explorer" in line for line in g.log)

def test_destroy_trade_row_scraps_and_refills():
    g = Game(("you", "cpu"))
    before = len([c for c in g.trade_row if c])
    g.destroy_trade_row(0)
    # one card moved to scrap, row refilled back to 5 items
    assert g.scrap_heap, "expected a card in scrap heap"
    assert len([c for c in g.trade_row if c]) == before

def test_topdeck_next_purchase_path():
    g = Game(("you","cpu"))
    p = g.current_player()
    # use first trade-row card as the purchase target
    card = g.trade_row[0]
    p.trade_pool = card["cost"]
    p.topdeck_next_purchase = True
    # spend & acquire via helpers like real flow
    g.spend_trade(p.name, card["cost"])
    g.acquire_from_trade_row(p.name, 0, destination="topdeck")
    assert p.deck and p.deck[0]["name"] == card["name"]