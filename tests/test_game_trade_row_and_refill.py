# starrealms/tests/test_game_trade_row_and_refill.py

from starrealms.game import Game

def test_refill_trade_row_keeps_slots_and_fills_nones():
    g = Game(("P1","P2"))

    # Remember names in slots so we can detect shifting
    original = [c["name"] if c else None for c in g.trade_row]

    # Remove a middle slot
    g.trade_row[2] = None
    g.refill_trade_row()

    assert len(g.trade_row) == 5
    # The None slot should be filled now
    assert g.trade_row[2] is not None

    # Neighboring slots should keep their original cards (no shift-left)
    assert g.trade_row[0]["name"] == original[0]
    assert g.trade_row[1]["name"] == original[1]
    assert g.trade_row[3]["name"] == original[3]
    assert g.trade_row[4]["name"] == original[4]