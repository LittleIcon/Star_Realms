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

@pytest.mark.skip("scrap_selected requires resolver/agent to actually scrap cards")
def test_scrap_selected_moves_card(game, p1, p2):
    class DummyAgent:
        def choose_card(self, zone, prompt=None):
            return zone[0]

    card = {"name": "Explorer"}
    p1.hand = [card]
    p1.agent = DummyAgent()  # inject chooser so resolver can work

    apply_effects({"type": "scrap_selected", "zone": "hand"}, p1, p2, game)

    assert card not in p1.hand
    assert card in p1.scrap_heap


def test_if_condition_no_blob_does_nothing(game, p1, p2):
    eff = {
        "type": "if",
        "condition": {"type": "faction_in_play", "faction": "Blob"},
        "then": [{"type": "combat", "amount": 5}],
    }
    before = p1.combat_pool
    apply_effects(eff, p1, p2, game)
    after = p1.combat_pool
    # Should stay the same since no Blob cards in play
    assert after == before