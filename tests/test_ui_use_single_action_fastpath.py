# tests/test_ui_use_single_action_fastpath.py

import builtins
import pytest

from starrealms.game import Game
from starrealms.cards import get_card_by_name
from starrealms.view import ui_common


def _call_use_menu(game, player):
    """
    Your project names this menu a few different ways in branches.
    Try the common ones; otherwise, skip so the failure is about code, not the test harness.
    """
    for name in ("ui_use", "use_menu", "menu_use", "run_use_menu"):
        fn = getattr(game, name, None)
        if callable(fn):
            return fn(player)
    pytest.skip("No public use-menu function found on Game (ui_use/use_menu/menu_use/run_use_menu)")


def _iter_inputs(monkeypatch, answers):
    """Feed a sequence of answers to ui_common.ui_input, one per call."""
    it = iter(answers)
    monkeypatch.setattr(ui_common, "ui_input", lambda prompt="": next(it))


def _capture_prints(monkeypatch):
    """Capture ui_common.ui_print output into a list so we can assert on it."""
    lines = []
    def _printer(*args, **kwargs):
        msg = " ".join(str(a) for a in args)
        lines.append(msg)
    monkeypatch.setattr(ui_common, "ui_print", _printer)
    return lines


def test_use_menu_skips_action_prompt_for_single_action_base(monkeypatch):
    """
    When a base has exactly ONE available action, the use flow should jump straight
    to the base's options (e.g., 'Options:'), without printing:
      - 'Available actions:'
      - 'Pick an action (1-based, or 'x' to cancel):'
    """
    g = Game(("you", "cpu"))
    p = g.current_player()
    o = g.opponent()
    p.human = True  # ensure the UI path is taken

    # Give the player Recycling Station (one activatable path that is a choose-one),
    # and make sure it's the first/only activatable item in the list to keep the test deterministic.
    rs = get_card_by_name(g.trade_deck + g.card_db, "Recycling Station").copy()
    p.bases[:] = [rs]  # just recycling station

    # We want to choose that base (index 1), then pick option 2 ("trade +1")
    printed = _capture_prints(monkeypatch)
    _iter_inputs(monkeypatch, ["1", "2"])  # pick base #1, then choose option #2

    # Run the use menu
    _call_use_menu(g, p)

    # Assertions:
    # 1) We DID show the options prompt
    assert any(line.strip().startswith("Options:") for line in printed), \
        f"Expected to see 'Options:' but got:\n" + "\n".join(printed)

    # 2) We DID NOT show the needless single-action prompts
    assert not any("Available actions:" in line for line in printed), \
        "Should skip 'Available actions:' when only one action exists"
    assert not any("Pick an action" in line for line in printed), \
        "Should skip 'Pick an action' when only one action exists"

    # 3) The effect should have applied; choosing option 2 is +1 trade.
    assert p.trade_pool == 1, "Choosing option 2 on Recycling Station should give +1 trade"