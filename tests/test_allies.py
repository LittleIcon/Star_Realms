import pytest

def _ally_ship(name, faction, ally_trade):
    return {
        "name": name, "type": "ship", "faction": faction,
        "on_play": [],
        "ally": [{"type": "trade", "amount": ally_trade}],
    }

@pytest.mark.mechanics
def test_ally_triggers_once_when_second_same_faction_enters(game, p1, p2):
    s1 = _ally_ship("Blobling A", "Blob", 2)
    s2 = _ally_ship("Blobling B", "Blob", 2)

    p1.in_play.append(s1)
    game.on_card_entered_play(p1)  # no ally yet (only one Blob)
    start = p1.trade_pool

    p1.in_play.append(s2)
    game.on_card_entered_play(p1)  # now ally should fire (once)
    assert p1.trade_pool >= start + 2

    # no double-trigger if we re-check
    again = p1.trade_pool
    game.resolve_allies(p1)
    assert p1.trade_pool == again
