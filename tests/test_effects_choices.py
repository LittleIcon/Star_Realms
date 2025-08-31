# tests/test_effects_choices.py
import pytest
from starrealms.effects import apply_effects


class DummyAgent:
    def choose_option(self, options, prompt=None):
        # Always pick the first option
        return options[0]

    def choose_card(self, zone, prompt=None):
        # Always pick the first available card
        return zone[0]


def test_choose_one_applies_selected_branch(game, p1, p2):
    p1.agent = DummyAgent()
    eff = {
        "type": "choose_one",
        "options": [
            {"label": "Trade", "effects": [{"type": "trade", "amount": 2}]},
            {"label": "Combat", "effects": [{"type": "combat", "amount": 3}]},
        ],
    }

    before_trade, before_combat = p1.trade_pool, p1.combat_pool
    apply_effects(eff, p1, p2, game)
    after_trade, after_combat = p1.trade_pool, p1.combat_pool

    # DummyAgent picked first option → trade
    assert after_trade == before_trade + 2
    assert after_combat == before_combat


def test_acquire_free_takes_card_from_trade_row(game, p1, p2):
    p1.agent = DummyAgent()

    # Fake a trade row with two cards
    card1 = {"name": "Scout", "cost": 1}
    card2 = {"name": "Viper", "cost": 2}
    game.trade_row = [card1, card2]

    eff = {"type": "acquire_free"}
    apply_effects(eff, p1, p2, game)

    # DummyAgent picked first card → should be in discard or hand
    assert (card1 in p1.discard_pile) or (card1 in p1.hand) or (card1 in p1.bases)
    assert card1 not in game.trade_row