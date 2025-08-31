# starrealms/tests/test_trade_and_ally_flags.py

from starrealms.game import Game
from starrealms.effects import apply_effect
from starrealms.view import ui_common


def test_destroy_trade_row_cancel_then_pick(monkeypatch):
    g = Game(("you", "cpu"))  # ensure human path is available
    p, o = g.current_player(), g.opponent()

    # Make sure there’s a card in slot 1 and capture its name
    assert g.trade_row and g.trade_row[0] is not None
    first_name = g.trade_row[0]["name"]
    before_len = len([c for c in g.trade_row if c])
    before_scrap = len(g.scrap_heap)

    # Cancel first: nothing should be removed or scrapped
    inputs = iter(["x"])
    monkeypatch.setattr(ui_common, "ui_input", lambda prompt="": next(inputs))
    apply_effect({"type": "destroy_target_trade_row"}, p, o, g)

    assert len([c for c in g.trade_row if c]) == before_len
    assert len(g.scrap_heap) == before_scrap

    # Now pick slot 1 (1-based index)
    inputs = iter(["1"])
    monkeypatch.setattr(ui_common, "ui_input", lambda prompt="": next(inputs))
    apply_effect({"type": "destroy_target_trade_row"}, p, o, g)

    # One more card in scrap, trade row still has 5 filled/None slots and slot refilled
    assert len(g.scrap_heap) == before_scrap + 1
    # The scrapped card should be the one we captured
    assert any(c["name"] == first_name for c in g.scrap_heap)
    # Row remains same size and refilled in place
    assert len(g.trade_row) == 5


def test_ally_any_faction_flag_lifecycle():
    g = Game(("P1", "P2"))
    p, o = g.current_player(), g.opponent()

    # Apply the effect: just verifies flag setting (behavioral ally math is engine-level)
    apply_effect({"type": "ally_any_faction"}, p, o, g)
    assert getattr(p, "ally_wildcard_active", False) is True

    # Flag should clear on end_turn
    p.end_turn()
    assert not hasattr(p, "ally_wildcard_active")