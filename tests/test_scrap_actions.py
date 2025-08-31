import pytest

def _scrap_ship(name, trade_on_scrap):
    return {
        "name": name, "type": "ship", "on_play": [],
        "scrap": [{"type": "trade", "amount": trade_on_scrap}],
    }

@pytest.mark.mechanics
def test_scrap_ship_moves_to_scrap_and_grants_trade(game, p1, p2):
    ship = _scrap_ship("Probe Frigate", 3)
    p1.in_play.append(ship)

    start_trade = p1.trade_pool
    start_in_play = len(p1.in_play)
    start_scrap = len(p1.scrap_heap)

    ok = p1.activate_ship(ship, p2, game, scrap=True)
    assert ok
    assert len(p1.in_play) == start_in_play - 1
    assert len(p1.scrap_heap) == start_scrap + 1
    assert p1.trade_pool == start_trade + 3
