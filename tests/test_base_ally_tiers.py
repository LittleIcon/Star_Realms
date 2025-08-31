import pytest

def test_base_ally_tiers_min_allies(game, p1, p2):
    # Base with two ally effects:
    #  - +2 trade when you have >=1 other Blob
    #  - +3 combat when you have >=2 other Blobs
    base = {
        "name": "Blob Command",
        "type": "base",
        "faction": "Blob",
        "defense": 3,
        "ally": [
            {"type": "trade", "amount": 2, "min_allies": 1},
            {"type": "combat", "amount": 3, "min_allies": 2},
        ],
    }
    sA = {"name": "Blob Scout", "type": "ship", "faction": "Blob", "on_play": []}
    sB = {"name": "Blob Ram",   "type": "ship", "faction": "Blob", "on_play": []}

    p1.bases[:] = [base]
    p1.in_play[:] = []

    # With 0 other Blobs → no ally
    t0, c0 = p1.trade_pool, p1.combat_pool
    game.resolve_allies(p1)
    assert (p1.trade_pool, p1.combat_pool) == (t0, c0)

    # Add first Blob → only the min_allies=1 effect (+2 trade) should apply
    p1.in_play.append(sA)
    game.resolve_allies(p1)
    assert p1.trade_pool == t0 + 2 and p1.combat_pool == c0

    # Clear ally flag to simulate a fresh base (or put into new turn)
    # (real game would do this at start_turn)
    base.setdefault("_rt", {})["ally_triggered"] = False

    # Add second Blob → both effects should apply (+2 trade, +3 combat)
    p1.in_play.append(sB)
    game.resolve_allies(p1)
    assert p1.trade_pool == t0 + 4 and p1.combat_pool == c0 + 3
