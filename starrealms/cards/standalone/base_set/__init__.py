# starrealms/cards/standalone/base_set/__init__.py
import json
from pathlib import Path

_here = Path(__file__).parent

with (_here / "cards.json").open("r", encoding="utf-8") as f:
    CARDS = json.load(f)

with (_here / "counts.json").open("r", encoding="utf-8") as f:
    COUNTS = json.load(f)

EXPLORER_NAME = "Explorer"


def build_trade_deck():
    """
    Return a list for the Base Set trade deck (80 cards).
    Copies card dicts so mutating in-game state doesn’t alter templates.
    """
    by_name = {c["name"]: c for c in CARDS}
    deck = []

    for name, n in COUNTS.items():
        proto = by_name.get(name)
        if not proto:
            raise ValueError(f"Base Set: '{name}' in counts.json not in cards.json")
        if proto.get("starter") or name == EXPLORER_NAME:
            continue
        for _ in range(int(n)):
            deck.append(proto.copy())

    # sanity checks (can relax while developing)
    if len(deck) != 80:
        raise AssertionError(f"Base Set deck should be 80 cards, got {len(deck)}")

    return deck