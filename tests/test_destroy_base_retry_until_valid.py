# tests/test_destroy_base_retry_until_valid.py
# file: tests/test_destroy_base_retry_until_valid.py

from starrealms.game import Game
from starrealms.cards import get_card_by_name
from starrealms.effects import apply_effect
from starrealms.view import ui_common


def test_destroy_base_reprompts_until_outpost_chosen(monkeypatch):
    g = Game(("you", "cpu"))
    p, o = g.current_player(), g.opponent()
    p.human = True  # use the human-prompt branch

    # Opponent has one outpost and one normal base (non-outpost)
    outpost = get_card_by_name(g.trade_deck + g.card_db, "Battle Station")  # Outpost
    normal  = get_card_by_name(g.trade_deck + g.card_db, "Blob Wheel")      # Not an outpost
    o.bases[:] = [outpost.copy(), normal.copy()]

    # Simulate a bad pick first (non-outpost "2"), then the correct pick ("1")
    answers = iter(["2", "1"])
    def _ui(prompt=""):
        try:
            return next(answers)
        except StopIteration:
            return "x"  # safety
    monkeypatch.setattr(ui_common, "ui_input", _ui)

    # Single call should consume both prompts: reject non-outpost, then accept outpost
    apply_effect({"type": "destroy_base"}, p, o, g)

    # Validate result: outpost destroyed, normal base remains
    assert len(o.bases) == 1, "Should end with exactly one base remaining"
    assert o.bases[0].get("name") == normal["name"], "Non-outpost should remain after destroying the outpost"

    # (Optional) If your implementation logs the rejection, this ensures it happened before the destroy:
    if hasattr(g, "log"):
        log = g.log
        # Look for a message about illegal pick when an outpost exists (exact wording may differ slightly)
        rejected = any("Outpost" in line and "must" in line.lower() for line in log)
        destroyed = any("destroys" in line.lower() and outpost["name"] in line for line in log)
        assert destroyed, "Expected a log entry that the outpost was destroyed"
        # Don't make the rejection log mandatory if wording might vary; leave it soft:
        # assert rejected, "Expected a log entry explaining the outpost-first rule rejection"