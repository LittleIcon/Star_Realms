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
