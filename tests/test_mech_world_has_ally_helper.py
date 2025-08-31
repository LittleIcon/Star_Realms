#test/test_mech_world_has_ally_helper.py

import pytest

from starrealms.game import Game

# Try to import the ally helper; skip tests if your code doesn't expose it yet.
try:
    from starrealms.engine.resolver import has_ally
except Exception:
    has_ally = None


def setup_game_nonhuman_actor():
    """Return (g, p, o) with p = non-human Player 2."""
    g = Game(("Player 1", "Player 2"))
    p = g.players[1]
    o = g.players[0]
    return g, p, o


def _mech_world_card():
    """Minimal Mech World: continuous 'ally any faction' while in play."""
    return {
        "name": "Mech World",
        "type": "base",
        "outpost": False,
        "effects": [{"type": "ally_any_faction", "trigger": "continuous"}],
    }


@pytest.mark.skipif(has_ally is None, reason="has_ally helper not exposed in resolver yet")
def test_has_ally_is_true_with_mech_world_active():
    g, p, o = setup_game_nonhuman_actor()

    # Put Mech World into play and notify dispatcher (so aura is active)
    mech = _mech_world_card()
    p.bases.append(mech)
    if hasattr(g, "dispatcher") and hasattr(g.dispatcher, "on_card_enter_play"):
        g.dispatcher.on_card_enter_play(p.name, mech)

    # With Mech World active, any faction ally check should pass
    assert has_ally(p, "Star Empire") is True
    assert has_ally(p, "Blob") is True
    assert has_ally(p, "Machine Cult") is True
    assert has_ally(p, "Trade Federation") is True


@pytest.mark.skipif(has_ally is None, reason="has_ally helper not exposed in resolver yet")
def test_has_ally_is_false_without_mech_world_and_no_same_faction_in_play():
    g, p, o = setup_game_nonhuman_actor()

    # No Mech World and no Star Empire cards in play
    assert has_ally(p, "Star Empire") is False