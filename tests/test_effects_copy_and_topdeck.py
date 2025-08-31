# tests/test_effects_copy_and_topdeck.py

import types
from starrealms.game import Game
from starrealms.effects import apply_effect
from starrealms.cards import EXPLORER_NAME
from starrealms.view import ui_common


def _ship(name, play_effect):
    """Minimal ship card with a single on-play effect."""
    return {
        "name": name,
        "type": "ship",
        "on_play": [play_effect],
    }


def test_copy_target_ship_ai_auto_picks_and_applies_effect():
    g = Game(("P1", "P2"))
    p, o = g.current_player(), g.opponent()

    # Put a target ship in play with a combat on-play effect,
    # followed by a 'source' ship to emulate Stealth Needle timing.
    target_ship = _ship("Target Ship", {"type": "combat", "amount": 3})
    source_ship = _ship("Source (Stealth Needle)", {"type": "trade", "amount": 1})
    p.in_play[:] = [target_ship, source_ship]

    start_trade, start_combat = p.trade_pool, p.combat_pool

    # Non-human branch should auto-pick the only eligible ship (target_ship)
    p.human = False
    apply_effect({"type": "copy_target_ship"}, p, o, g)

    # Expect the copied ship's on-play effect to apply (+3 combat)
    assert p.combat_pool >= start_combat + 3
    # Source's own effect should not have been applied by the copy
    assert p.trade_pool == start_trade


def test_copy_target_ship_human_cancel_no_change(monkeypatch):
    g = Game(("you", "cpu"))  # "you" -> human
    p, o = g.current_player(), g.opponent()

    # Put one eligible target and a 'source' last
    target_ship = _ship("Target Ship", {"type": "combat", "amount": 2})
    source_ship = _ship("Source (Stealth Needle)", {"type": "trade", "amount": 1})
    p.in_play[:] = [target_ship, source_ship]

    start_trade, start_combat = p.trade_pool, p.combat_pool

    # Human path: simulate user cancel ('x')
    inputs = iter(["x"])
    monkeypatch.setattr(ui_common, "ui_input", lambda prompt="": next(inputs))
    apply_effect({"type": "copy_target_ship"}, p, o, g)

    # No change because the user cancelled the selection
    assert p.combat_pool == start_combat
    assert p.trade_pool == start_trade


def test_topdeck_next_purchase_puts_explorer_on_top():
    g = Game(("P1", "P2"))
    p, _ = g.current_player(), g.opponent()

    # Mark next purchase to be top-decked
    apply_effect({"type": "topdeck_next_purchase"}, p, g.opponent(), g)

    # Give enough trade and buy an Explorer via game helper
    p.trade_pool = 2
    g.buy_explorer(p)

    # Draw one: should be Explorer because it was top-decked
    drawn = p.draw_card()
    assert drawn is not None
    assert drawn.get("name") == EXPLORER_NAME