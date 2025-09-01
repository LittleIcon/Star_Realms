# tests/test_blob_destroyer_choice.py
#
# Ensures Blob Destroyer (with ally) asks ONCE to choose between
# destroying an opponent base (respecting Outpost-first) OR scrapping
# a trade-row card — and supports cancel.

import pytest

from starrealms.game import Game
from starrealms.cards import get_card_by_name
from starrealms.view import ui_common


def _iter_inputs(monkeypatch, answers):
    it = iter(answers)
    monkeypatch.setattr(ui_common, "ui_input", lambda prompt="": next(it))


def _capture_prints(monkeypatch):
    lines = []
    def _printer(*args, **kwargs):
        msg = " ".join(str(a) for a in args)
        lines.append(msg)
    monkeypatch.setattr(ui_common, "ui_print", _printer)
    return lines


def _play_card_by_name(game, player, opponent, name):
    card = get_card_by_name(game.trade_deck + game.card_db, name)
    # some test harnesses require a copy
    card = card.copy()
    player.hand.append(card)
    assert player.play_card(card, opponent, game) is True
    return card


def test_blob_destroyer_choice_cancel(monkeypatch):
    """
    If the user cancels the unified choice, neither a base nor a trade-row
    card is destroyed/scrapped, and we only saw ONE choice prompt.
    """
    g = Game(("you", "cpu"))
    p = g.current_player(); p.human = True
    o = g.opponent()

    # Ensure an ally is present so Blob Destroyer's ally effect is active
    _play_card_by_name(g, p, o, "Blob Fighter")  # provides Blob ally
    # Give opponent a non-outpost base so there is a valid base target IF no outpost
    o.bases.append({"name": "Barter World", "type": "base", "defense": 4, "outpost": False})
    # Ensure trade row has something scrap-able
    if not getattr(g, "trade_row", None):
        g.trade_row = [{"name": "Explorer", "cost": 2} for _ in range(5)]

    printed = _capture_prints(monkeypatch)

    # User cancels at the unified choice
    _iter_inputs(monkeypatch, ["x"])

    _play_card_by_name(g, p, o, "Blob Destroyer")

    # Only one unified choice prompt should have appeared
    assert any("Destroy" in line and "base" in line and "trade" in line for line in printed), \
        "Expected a single unified prompt offering base vs trade-row"
    assert printed.count(next(l for l in printed if "Destroy" in l and "base" in l and "trade" in l)) == 1, \
        "Prompt should appear exactly once"

    # Nothing should be destroyed/scrapped
    assert any(b.get("name") == "Barter World" for b in o.bases), "Base should remain after cancel"
    assert sum(1 for c in g.trade_row if c) == 5, "Trade row should be unchanged after cancel"


def test_blob_destroyer_choice_trade_row(monkeypatch):
    """
    Choosing 'trade row' scraps exactly one trade-row slot and refills it.
    We still see only a single unified prompt.
    """
    g = Game(("you", "cpu"))
    p = g.current_player(); p.human = True
    o = g.opponent()

    _play_card_by_name(g, p, o, "Blob Fighter")  # ally enabled

    # Build a deterministic trade row & trade deck
    g.trade_row = [
        {"name": "Supply Bot", "cost": 3},
        {"name": "Explorer",   "cost": 2},
        {"name": "Scout*",     "cost": 0},
        {"name": "Viper*",     "cost": 0},
        {"name": "Cutter",     "cost": 2},
    ]
    g.trade_deck = [{"name": "Top Refiller", "cost": 5}] + (g.trade_deck or [])

    printed = _capture_prints(monkeypatch)
    # Answer 't' (or '2') for trade-row path, then pick slot '2'
    _iter_inputs(monkeypatch, ["t", "2"])

    _play_card_by_name(g, p, o, "Blob Destroyer")

    # Unified choice prompt shown once
    assert any("Destroy" in line and "base" in line and "trade" in line for line in printed), \
        "Expected unified base vs trade-row prompt"
    assert printed.count(next(l for l in printed if "Destroy" in l and "base" in l and "trade" in l)) == 1

    # Slot 2 should have been scrapped and refilled by 'Top Refiller'
    assert g.trade_row[1] and g.trade_row[1].get("name") == "Top Refiller", \
        "Chosen trade-row slot should be replaced from the trade deck"

    # No base destroyed
    # (opponent has no bases here; just ensure no stray 'destroy base' happened)
    assert not getattr(g, "destroyed_traderow", []) or 1 in g.destroyed_traderow, \
        "Expect only trade-row destruction to be recorded"


def test_blob_destroyer_choice_base_outpost_first(monkeypatch):
    """
    Choosing 'base' enforces the Outpost-first rule:
    - If an Outpost exists, picking a non-outpost is rejected (single prompt only),
      and nothing happens.
    - Picking the Outpost is allowed and destroys it.
    """
    g = Game(("you", "cpu"))
    p = g.current_player(); p.human = True
    o = g.opponent()

    _play_card_by_name(g, p, o, "Blob Fighter")  # ally enabled

    # Opponent has an Outpost and a normal base
    o.bases[:] = [
        {"name": "Space Station", "type": "base", "defense": 4, "outpost": True},
        {"name": "Barter World",  "type": "base", "defense": 4, "outpost": False},
    ]

    printed = _capture_prints(monkeypatch)

    # First attempt: choose base path, then try to pick the NON-outpost (index 2)
    # Unified prompt → 'b', then UI list appears → choose "2" (illegal), should reject and return
    _iter_inputs(monkeypatch, ["b", "2"])
    _play_card_by_name(g, p, o, "Blob Destroyer")

    # Outpost still present after illegal pick
    assert any(b.get("name") == "Space Station" for b in o.bases), "Outpost must remain after illegal pick"
    # Only one pass through prompts (no re-prompt loops)
    assert printed.count(next(l for l in printed if "Destroy" in l and "base" in l and "trade" in l)) == 1

    # Second attempt in same test: play another Blob Destroyer and pick the Outpost (index 1)
    printed.clear()
    _iter_inputs(monkeypatch, ["b", "1"])
    _play_card_by_name(g, p, o, "Blob Destroyer")

    # Outpost should now be destroyed
    assert not any(b.get("name") == "Space Station" for b in o.bases), "Outpost should be destroyed when chosen"