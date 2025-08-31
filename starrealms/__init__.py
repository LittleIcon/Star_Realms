# starrealms/__init__.py

"""
Star Realms - Base Set Engine
This package contains the core logic for simulating and playing Star Realms.
"""

__version__ = "0.1.0"

# starrealms/__init__.py

from .cards import CARDS
from .player import Player
from .game import Game

__all__ = [
    "CARDS",
    "Player",
    "Game",
]
