# tests/test_destroy_base_outpost_rule.py
# file: tests/test_destroy_base_outpost_rule.py

from starrealms.game import Game
from starrealms.cards import get_card_by_name
from starrealms.effects import apply_effect
from starrealms.view import ui_common

def test_destroy_base_requires_outpost_first(monkeypatch):
    g = Game(("you", "cpu"))
    p, o = g.current_player(), g.opponent()
    p.human = True  # trigger the human-prompt path in effects.destroy_base

    # Put two opponent bases in play: one Outpost and one normal base
    battle_station = get_card_by_name(g.trade_deck + g.card_db, "Battle Station")  # outpost
    blob_wheel     = get_card_by_name(g.trade_deck + g.card_db, "Blob Wheel")      # non-outpost
    assert battle_station and blob_wheel
    o.bases[:] = [battle_station.copy(), blob_wheel.copy()]

    # 1) Human selects the NON-outpost base while an outpost exists -> should do nothing
    inputs = iter(["2"])  # Blob Wheel (non-outpost)
    monkeypatch.setattr(ui_common, "ui_input", lambda prompt="": next(inputs))
    before = list(o.bases)
    apply_effect({"type": "destroy_base"}, p, o, g)
    assert o.bases == before, "Should NOT destroy a non-outpost while an outpost is present"

    # 2) Human now selects the OUTPOST -> it should be destroyed
    inputs = iter(["1"])  # Battle Station (outpost)
    monkeypatch.setattr(ui_common, "ui_input", lambda prompt="": next(inputs))
    apply_effect({"type": "destroy_base"}, p, o, g)
    assert len(o.bases) == 1, "One base should remain after destroying the outpost"
    assert o.bases[0].get("name") == "Blob Wheel", "The remaining base should be the non-outpost"