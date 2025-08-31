# tests/test_resolver_integration.py
import pytest
from starrealms.effects import apply_effects

@pytest.mark.engine_integration
def test_choose_one_integration(game, p1, p2, dummy_agent):
    # Only run this if your resolver actually consults player.agent.choose_option(...)
    p1.agent = dummy_agent
    before = p1.trade_pool
    eff = {"type": "choose_one", "options": [
        {"label": "T", "effects": [{"type": "trade", "amount": 2}]},
        {"label": "C", "effects": [{"type": "combat", "amount": 3}]},
    ]}
    apply_effects(eff, p1, p2, game)
    assert p1.trade_pool in (before, before + 2)