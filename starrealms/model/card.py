"""
model/card.py

Temporary stub for Explorer and trade deck construction.
This will later be replaced with real card data loaded
from cards.json and counts.json.
"""

EXPLORER_NAME = "Explorer"

EXPLORER = {
    "name": EXPLORER_NAME,
    "faction": "Neutral",
    "type": "ship",
    "cost": 2,
    "on_play": [{"type": "trade", "amount": 2}],
    "scrap": [{"type": "combat", "amount": 2}],
}


def build_trade_deck():
    """
    TEMP: build a fake trade deck consisting of 50 Explorer copies.
    Each card is an independent dict so mutations don't leak.
    """
    return [EXPLORER.copy() for _ in range(50)]
