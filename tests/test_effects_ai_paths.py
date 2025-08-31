# starrealms/tests/test_effects_ai_paths.py
import pytest
from starrealms.game import Game
from starrealms.effects import apply_effect

def test_destroy_base_ai_respects_outpost_and_notifies():
    # Names are NOT "you"/"player 1" so both players are non-human (AI path)
    g = Game(("P1", "P2"))
    p = g.current_player()
    o = g.opponent()

    # Opponent has an Outpost and a normal base
    outpost = {"name": "Outpost A", "type": "base", "defense": 3, "outpost": True}
    normal  = {"name": "Base B",   "type": "base", "defense": 5, "outpost": False}
    o.bases[:] = [outpost, normal]

    # Spy on dispatcher to ensure on_card_leave_play is invoked when destroyed
    calls = []
    orig_leave = getattr(g.dispatcher, "on_card_leave_play", None)
    def spy_leave(owner_name, base_card):
        calls.append(("leave", owner_name, base_card.get("name")))
        if orig_leave:
            orig_leave(owner_name, base_card)
    g.dispatcher.on_card_leave_play = spy_leave

    # AI path should auto-destroy the outpost first
    apply_effect({"type": "destroy_base"}, p, o, g)
    assert len(o.bases) == 1
    assert o.bases[0]["name"] == "Base B"
    assert any(c for c in calls if c == ("leave", o.name, "Outpost A"))

    # Next destruction removes remaining (normal) base and notifies
    apply_effect({"type": "destroy_base"}, p, o, g)
    assert len(o.bases) == 0
    assert any(c for c in calls if c == ("leave", o.name, "Base B"))