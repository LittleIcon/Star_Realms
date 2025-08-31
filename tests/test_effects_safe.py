# tests/test_effects_safe.py
import pytest
from starrealms.effects import apply_effects


def test_trade_and_combat_pools(game, p1, p2):
    before_t, before_c = p1.trade_pool, p1.combat_pool
    apply_effects({"type": "trade", "amount": 3}, p1, p2, game)
    apply_effects({"type": "combat", "amount": 4}, p1, p2, game)
    assert p1.trade_pool == before_t + 3
    assert p1.combat_pool == before_c + 4


def test_authority_gain_self_and_damage_opponent(game, p1, p2):
    a1, a2 = p1.authority, p2.authority
    apply_effects({"type": "authority", "amount": 5}, p1, p2, game)
    apply_effects({"type": "authority", "amount": -7}, p2, p1, game)
    assert p1.authority == a1 + 5
    assert p2.authority == a2 - 7


def test_draw_basic_and_reshuffle(game, p1, p2):
    # Ensure a simple draw
    start = len(p1.hand)
    # seed small deck
    p1.deck[:] = [{"name": "C1"}, {"name": "C2"}]
    apply_effects({"type": "draw", "amount": 2}, p1, p2, game)
    assert len(p1.hand) == start + 2

    # Now test reshuffle: move a card to discard, empty deck, draw 1
    p1.discard_pile.append({"name": "DX"})
    p1.deck.clear()
    h0 = len(p1.hand)
    apply_effects({"type": "draw", "amount": 1}, p1, p2, game)
    # the discard card should have been reshuffled and drawn
    names = {c["name"] for c in p1.hand}
    assert len(p1.hand) == h0 + 1
    assert "DX" in names


def test_discard_then_draw_net_hand_unchanged(game, p1, p2):
    # ensure at least 3 in hand
    while len(p1.hand) < 3:
        p1.draw_card()
    start = len(p1.hand)
    apply_effects({"type": "discard_then_draw", "amount": 2}, p1, p2, game)
    assert len(p1.hand) == start  # discard 2 then draw 2


def test_discard_noop_when_empty(game, p1, p2):
    p1.hand.clear()
    apply_effects({"type": "discard", "amount": 1}, p1, p2, game)
    assert p1.hand == []  # no crash / no change


def test_scrap_selected_noop_without_resolver(game, p1, p2):
    # With no agent/resolver wiring in unit tests, this should be a safe no-op
    card = {"name": "Explorer"}
    p1.hand = [card]
    apply_effects({"type": "scrap_selected", "zone": "hand"}, p1, p2, game)
    assert card in p1.hand
    assert card not in p1.scrap_heap


def test_if_condition_without_else_does_nothing(game, p1, p2):
    # No Blob in play → then should not fire; your engine ignores missing else.
    before_c = p1.combat_pool
    eff = {
        "type": "if",
        "condition": {"type": "faction_in_play", "faction": "Blob"},
        "then": [{"type": "combat", "amount": 5}],
    }
    apply_effects(eff, p1, p2, game)
    assert p1.combat_pool == before_c


def test_apply_effects_accepts_list_and_single(game, p1, p2):
    # single dict
    apply_effects({"type": "trade", "amount": 1}, p1, p2, game)
    # list of dicts
    t0, c0 = p1.trade_pool, p1.combat_pool
    apply_effects([{"type": "trade", "amount": 2}, {"type": "combat", "amount": 3}], p1, p2, game)
    assert p1.trade_pool == t0 + 2
    assert p1.combat_pool == c0 + 3