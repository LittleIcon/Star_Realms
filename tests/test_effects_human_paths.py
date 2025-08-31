# starrealms/tests/test_effects_human_paths.py

import pytest
from starrealms.game import Game
from starrealms.effects import apply_effect

def _input_iter(monkeypatch, answers):
    """
    Patch BOTH the symbol bound inside starrealms.effects and the source ui_common
    so any call to ui_input consumes our scripted responses.
    """
    it = iter(answers)

    def _fake_input(prompt=""):
        try:
            return next(it)
        except StopIteration:
            return "x"  # default safe cancel

    # Patch the bound name inside effects.py
    import starrealms.effects as effmod
    monkeypatch.setattr(effmod, "ui_input", _fake_input, raising=True)

    # Patch the original provider too (for any code that reaches it directly)
    import starrealms.view.ui_common as ui_common
    monkeypatch.setattr(ui_common, "ui_input", _fake_input, raising=True)

    return it

def test_discard_then_draw_human_discards_one_then_stops(monkeypatch):
    g = Game(("you", "cpu"))  # Player 1 ("you") is human
    p = g.current_player()
    o = g.opponent()

    p.hand[:] = [{"name": "H1"}, {"name": "H2"}, {"name": "H3"}]
    p.deck[:] = [{"name": "N1"}, {"name": "N2"}, {"name": "N3"}]

    # Discard index 2 (H2), then stop
    _input_iter(monkeypatch, ["2", "x"])

    before_hand = [c["name"] for c in p.hand]
    apply_effect({"type": "discard_then_draw", "amount": 2}, p, o, g)

    # One discarded to discard_pile, one drawn from deck
    assert [c["name"] for c in p.hand] != before_hand
    assert any(c["name"] == "H2" for c in p.discard_pile), "H2 should be discarded"

def test_scrap_multiple_human_mixed_piles(monkeypatch):
    g = Game(("you", "cpu"))
    p = g.current_player()
    o = g.opponent()

    p.hand[:] = [{"name": "H1"}, {"name": "H2"}]
    p.discard_pile[:] = [{"name": "D1"}]
    # NOTE: engine uses game.scrap_heap when present
    g.scrap_heap[:] = []

    # Choose discard (scrap D1), then hand (scrap H2), then stop
    _input_iter(monkeypatch, ["d", "1", "h", "2", "x"])

    apply_effect({"type": "scrap_multiple", "amount": 2}, p, o, g)
    scrapped_names = [c["name"] for c in g.scrap_heap]
    assert "D1" in scrapped_names and "H2" in scrapped_names
    assert "H1" not in scrapped_names

def test_destroy_base_human_destroys_outpost(monkeypatch):
    g = Game(("you", "cpu"))
    p = g.current_player()
    o = g.opponent()

    # Opponent has an Outpost and a normal base
    outpost = {"name": "Outpost A", "type": "base", "defense": 3, "outpost": True}
    normal  = {"name": "Base B",   "type": "base", "defense": 5, "outpost": False}
    o.bases[:] = [outpost, normal]

    # Choose the outpost first (index 1 in the printed list)
    _input_iter(monkeypatch, ["1"])
    apply_effect({"type": "destroy_base"}, p, o, g)

    # Outpost gone; normal base remains. (Human path doesn’t notify dispatcher.)
    assert len(o.bases) == 1
    assert o.bases[0]["name"] == "Base B"

# starrealms/tests/test_effects_human_paths.py

def test_destroy_trade_row_human_cancel_then_pick(monkeypatch):
    g = Game(("you", "cpu"))
    p = g.current_player()
    o = g.opponent()

    # Ensure trade row exists
    assert g.trade_row and g.trade_row[0] is not None
    len_before = len(g.trade_row)

    # Cancel first — ensure row size unchanged (engine may still append to scrap_heap)
    _input_iter(monkeypatch, ["x"])
    apply_effect({"type": "destroy_target_trade_row"}, p, o, g)
    assert len(g.trade_row) == len_before
    scrap_len_mid = len(g.scrap_heap)

    # Now remove index 1 — row size stays constant; scrap heap should grow by exactly 1
    _input_iter(monkeypatch, ["1"])
    apply_effect({"type": "destroy_target_trade_row"}, p, o, g)
    assert len(g.trade_row) == len_before
    assert len(g.scrap_heap) == scrap_len_mid + 1

def test_copy_target_ship_human_choice(monkeypatch):
    g = Game(("you", "cpu"))
    p = g.current_player()
    o = g.opponent()

    # Two ships in play; last is the 'source' (excluded from eligible)
    ship_a = {"name": "Ship A", "type": "ship", "on_play": [{"type": "combat", "amount": 3}]}
    ship_b = {"name": "Ship B", "type": "ship", "on_play": [{"type": "trade",  "amount": 2}]}
    p.in_play[:] = [ship_a, ship_b]
    start_trade, start_combat = p.trade_pool, p.combat_pool

    # Human chooses index 1 (Ship A)
    _input_iter(monkeypatch, ["1"])
    apply_effect({"type": "copy_target_ship"}, p, o, g)

    # Copying Ship A applies +3 combat (not +2 trade)
    assert p.combat_pool == start_combat + 3
    assert p.trade_pool == start_trade