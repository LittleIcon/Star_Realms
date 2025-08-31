import pytest
from starrealms.game import Game

@pytest.fixture
def game():
    return Game(("P1","P2"))

@pytest.fixture
def p1(game):
    return game.players[0]

@pytest.fixture
def p2(game):
    return game.players[1]

# tests/conftest.py
import pytest

class DummyAgent:
    """Always picks the first option/card if available."""
    def choose_card(self, zone, prompt=None):
        return zone[0] if zone else None
    def choose_option(self, options, prompt=None):
        return options[0] if options else None

@pytest.fixture
def dummy_agent():
    return DummyAgent()

# Mark factories (useful if you want to group/skip by marker)
def pytest_configure(config):
    config.addinivalue_line("markers", "needs_resolver: test requires resolver/agent wiring")
    config.addinivalue_line("markers", "engine_integration: crosses module boundaries (resolver/dispatcher)")