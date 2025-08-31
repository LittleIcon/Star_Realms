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
    Return the Base Set trade deck built from counts.json.

    - Excludes starters and Explorer (Explorer is a separate unlimited supply).
    - Returns shallow copies so per-instance runtime flags are safe.
    - Validates that counts only reference known card names.
    """
    by_name = {c["name"]: c for c in CARDS}

    # Sanity: Explorer should exist in the dataset even if excluded from the deck
    if EXPLORER_NAME not in by_name:
        raise ValueError(f"'{EXPLORER_NAME}' missing from cards.json")

    deck = []
    expected = 0

    for name, n in COUNTS.items():
        if name not in by_name:
            raise ValueError(f"counts.json references unknown card: {name}")
        n = int(n)

        proto = by_name[name]
        # Skip starters and Explorer from the trade deck
        if proto.get("starter") or name == EXPLORER_NAME:
            continue

        expected += n
        deck.extend(proto.copy() for _ in range(n))

    # Optional: consistency check derived from counts.json
    if len(deck) != expected:
        raise AssertionError(
            f"Trade deck size mismatch: expected {expected}, got {len(deck)}"
        )

    return deck
