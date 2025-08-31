# tests/test_mech_world_ally_redout.py

import pytest
from starrealms.game import Game

def setup_game_nonhuman_actor():
    """Return (g, p, o) where p is NON-human actor (Player 2) and o is opponent (Player 1)."""
    g = Game(("Player 1", "Player 2"))
    p = g.players[1]  # Player 2 is non-human by default
    o = g.players[0]
    return g, p, o

def _mech_world_card():
    """
    Minimal Mech World representation:
    - Base, continuous effect: counts as all factions while in play.
    """
    return {
        "name": "Mech World",
        "type": "base",
        "outpost": False,
        # Dispatcher recognizes this as a continuous ally-any-faction aura
        "effects": [{"type": "ally_any_faction", "trigger": "continuous"}],
    }

def _royal_redoubt_card():
    """
    Royal Redoubt (Star Empire) with an ALLY that forces opponent to discard 1.
    """
    return {
        "name": "Royal Redoubt",
        "type": "base",
        "faction": "Star Empire",
        "effects": [
            {"trigger": "ally", "type": "opponent_discards", "amount": 1},
        ],
    }

def _play_via_engine_or_fallback(g, p, o, card):
    """Play `card` using the engine, or fall back to placing it in bases and notifying dispatcher."""
    if hasattr(p, "play_card"):
        ok = p.play_card(card, o, g)
        if not ok:
            p.hand.append(card)
            assert p.play_card(card, o, g)
    else:
        p.bases.append(card)
        if hasattr(g, "dispatcher") and hasattr(g.dispatcher, "on_card_enter_play"):
            g.dispatcher.on_card_enter_play(p.name, card)

def test_royal_redoubt_ally_triggers_with_mech_world_in_play():
    g, p, o = setup_game_nonhuman_actor()

    # Ensure opponent has at least 1 card to discard
    if not o.hand:
        o.hand.append({"name": "Filler", "type": "ship"})

    # Put Mech World into play and notify dispatcher so its aura is active
    mech_world = _mech_world_card()
    p.bases.append(mech_world)
    if hasattr(g, "dispatcher") and hasattr(g.dispatcher, "on_card_enter_play"):
        g.dispatcher.on_card_enter_play(p.name, mech_world)

    # Play Royal Redoubt
    royal = _royal_redoubt_card()
    start_hand = len(o.hand)
    start_discards = len(o.discard_pile)

    _play_via_engine_or_fallback(g, p, o, royal)

    # Expect exactly one standard discard (hand -1, discard_pile +1)
    assert len(o.discard_pile) - start_discards == 1
    assert start_hand - len(o.hand) == 1

def test_royal_redoubt_ally_does_not_trigger_without_mech_world():
    g, p, o = setup_game_nonhuman_actor()

    # Ensure opponent has at least 1 card to discard
    if not o.hand:
        o.hand.append({"name": "Filler", "type": "ship"})

    royal = _royal_redoubt_card()
    start_hand = len(o.hand)
    start_discards = len(o.discard_pile)

    _play_via_engine_or_fallback(g, p, o, royal)

    # Without wildcard or same-faction present, ally shouldn't fire
    assert len(o.discard_pile) - start_discards == 0
    assert start_hand - len(o.hand) == 0