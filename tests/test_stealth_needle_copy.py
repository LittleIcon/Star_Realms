# tests/test_stealth_needle_copy.py
import pytest

from starrealms.game import Game

# optional UI helper; if not present, we’ll skip the 3rd test
try:
    from starrealms.view.ui_common import describe_card  # type: ignore
except Exception:
    describe_card = None


def _iter_inputs(monkeypatch, answers):
    """Monkeypatch ui_input to return items from answers sequentially."""
    from starrealms.view import ui_common
    it = iter(answers)
    monkeypatch.setattr(ui_common, "ui_input", lambda prompt="": next(it))


def _ship(name, combat=0, draw=0):
    """Minimal ship with on_play effects for easy observability."""
    effs = []
    if combat:
        effs.append({"type": "combat", "amount": combat})
    if draw:
        effs.append({"type": "draw", "amount": draw})
    return {
        "name": name,
        "type": "ship",
        "faction": "Neutral",
        "on_play": effs,
    }


def _stealth_needle():
    return {
        "name": "Stealth Needle",
        "type": "ship",
        "faction": "Machine Cult",
        "activated": [
            {"type": "copy_target_ship"}
        ],
    }


def test_stealth_needle_prompts_and_copies_selected_ship(monkeypatch):
    # Setup game; make player 1 human so the copy prompt path is used
    g = Game(("you", "cpu"))
    p = g.players[0]
    o = g.players[1]
    p.human = True

    # Play two ships so there are multiple eligible copy targets
    a = _ship("Gunship A", combat=2)     # eligible index 1
    b = _ship("Survey B", combat=0, draw=1)  # eligible index 2 (we will choose this)
    sn = _stealth_needle()

    # Put ships into hand, then play them via engine path
    p.hand.extend([a, b, sn])
    assert p.play_card(a, o, g) is True
    assert p.play_card(b, o, g) is True
    assert p.play_card(sn, o, g) is True

    # Activate Stealth Needle, choose "2" to copy Survey B
    _iter_inputs(monkeypatch, ["2"])
    # mark which card is being activated (your Player.activate_ship should set this automatically;
    # if it doesn’t in your build, we do it defensively here)
    setattr(p, "_activating_card", sn)
    before_combat = p.combat_pool
    assert p.activate_ship(sn, o, g, scrap=False) is True

    # It should have recorded what it copied on the activator
    assert sn.get("_copied_from_name") == "Survey B"
    # And the card reference should be stored
    assert sn.get("_copied_from") is not None
    # On-play of Survey B draws 1; combat didn't change, but draw is hard to assert without deck control.
    # We at least ensure combat wasn't altered by copying a non-combat ship.
    assert p.combat_pool == before_combat


def test_stealth_needle_logs_copy_action(monkeypatch):
    g = Game(("you", "cpu"))
    p = g.players[0]
    o = g.players[1]
    p.human = True

    a = _ship("Corvette", combat=2)
    sn = _stealth_needle()

    p.hand.extend([a, sn])
    assert p.play_card(a, o, g)
    assert p.play_card(sn, o, g)

    # Only one eligible ship (Corvette) => choose index 1
    _iter_inputs(monkeypatch, ["1"])
    setattr(p, "_activating_card", sn)
    p.activate_ship(sn, o, g, scrap=False)

    # log should mention that Stealth Needle copies Corvette
    joined_log = "\n".join(getattr(g, "log", []))
    assert "Stealth Needle" in joined_log and "copies Corvette" in joined_log


@pytest.mark.skipif(describe_card is None, reason="describe_card not exposed in ui_common")
def test_info_describes_copied_ship(monkeypatch):
    g = Game(("you", "cpu"))
    p = g.players[0]
    o = g.players[1]
    p.human = True

    a = _ship("Patrol Mech", combat=3)
    sn = _stealth_needle()

    p.hand.extend([a, sn])
    assert p.play_card(a, o, g)
    assert p.play_card(sn, o, g)

    # choose to copy Patrol Mech
    _iter_inputs(monkeypatch, ["1"])
    setattr(p, "_activating_card", sn)
    p.activate_ship(sn, o, g, scrap=False)

    # describe_card should include the "Copying: Patrol Mech" line
    text = describe_card(sn)
    assert "Copying: Patrol Mech" in text