# starrealms/tests/test_destroy_base_paths.py
from starrealms.game import Game
from starrealms.effects import apply_effect
from starrealms.view import ui_common


def _iter_inputs(monkeypatch, answers):
    it = iter(answers)
    monkeypatch.setattr(ui_common, "ui_input", lambda prompt="": next(it))


def test_destroy_base_human_respects_outpost_then_destroys(monkeypatch):
    g = Game(("you", "cpu"))  # "you" -> human path enabled
    p = g.current_player()
    o = g.opponent()

    # Opponent has an Outpost and a normal base
    outpost = {"name": "Outpost A", "type": "base", "defense": 4, "outpost": True}
    normal  = {"name": "Base B",   "type": "base", "defense": 5, "outpost": False}
    o.bases[:] = [outpost, normal]

    # Spy on dispatcher to ensure it’s called when a base leaves play
    calls = []
    orig = getattr(g.dispatcher, "on_card_leave_play", None)

    def spy(owner_name, base_card):
        calls.append(("leave", owner_name, base_card.get("name")))
        if orig:
            orig(owner_name, base_card)

    g.dispatcher.on_card_leave_play = spy

    # 1) Try to destroy the normal base while an outpost exists (should do nothing)
    _iter_inputs(monkeypatch, ["2"])  # human chooses the non-outpost (index 2)
    apply_effect({"type": "destroy_base"}, p, o, g)
    assert len(o.bases) == 2  # still both there
    assert all(b in o.bases for b in (outpost, normal))
    assert not calls  # no on_card_leave_play yet

    # 2) Now destroy the Outpost (index 1)
    _iter_inputs(monkeypatch, ["1"])
    apply_effect({"type": "destroy_base"}, p, o, g)
    assert len(o.bases) == 1
    assert o.bases[0]["name"] == "Base B"
    assert any(ev for ev in calls if ev == ("leave", o.name, "Outpost A"))

    # 3) With no outpost remaining, destroy the remaining base
    _iter_inputs(monkeypatch, ["1"])  # the remaining base is at index 1 now
    apply_effect({"type": "destroy_base"}, p, o, g)
    assert len(o.bases) == 0
    assert any(ev for ev in calls if ev == ("leave", o.name, "Base B"))