"""
starters.py
Defines starting decks for players across sets/expansions.
"""

# Base Set starting deck
BASE_STARTER = [
    {"name": "Scout", "type": "ship", "faction": "neutral", "cost": 0, "effects": [{"trade": 1}]} for _ in range(8)
] + [
    {"name": "Viper", "type": "ship", "faction": "neutral", "cost": 0, "effects": [{"combat": 1}]} for _ in range(2)
]