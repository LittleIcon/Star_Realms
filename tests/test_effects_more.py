# tests/test_effects_more.py
import pytest
from starrealms.effects import apply_effects


def test_trade_and_combat_increase_resources(game, p1, p2):
    before_trade = p1.trade_pool
    before_combat = p1.combat_pool

    apply_effects({"type": "trade", "amount": 3}, p1, p2, game)
    apply_effects({"type": "combat", "amount": 4}, p1, p2, game)

    assert p1.trade_pool == before_trade + 3
    assert p1.combat_pool == before_combat + 4


def test_authority_gain_and_loss(game, p1, p2):
    start1, start2 = p1.authority, p2.authority
    apply_effects({"type": "authority", "amount": 5}, p1, p2, game)
    apply_effects({"type": "authority", "amount": -3}, p2, p1, game)
    assert p1.authority == start1 + 5
    assert p2.authority == start2 - 3


@pytest.mark.skip("scrap_selected needs resolver/agent integration to test properly")
def test_scrap_selected_moves_card(game, p1, p2):
    card = {"name": "Explorer"}
    p1.hand = [card]
    apply_effects({"type": "scrap_selected", "zone": "hand"}, p1, p2, game)
    assert card not in p1.hand
    assert card in p1.scrap_heap


@pytest.mark.skip("choose_one uses resolver/agent, not Player; needs integration test")
def test_choose_one_branches(game, p1, p2):
    eff = {
        "type": "choose_one",
        "options": [
            {"label": "OptionA", "effects": [{"type": "trade", "amount": 2}]},
            {"label": "OptionB", "effects": [{"type": "combat", "amount": 3}]},
        ],
    }
    apply_effects(eff, p1, p2, game)
    assert p1.trade_pool > 0 or p1.combat_pool > 0


def test_if_condition_does_nothing_without_blob(game, p1, p2):
    eff = {
        "type": "if",
        "condition": {"type": "faction_in_play", "faction": "Blob"},
        "then": [{"type": "combat", "amount": 5}],
    }
    before = p1.combat_pool
    apply_effects(eff, p1, p2, game)
    after = p1.combat_pool
    assert after == before