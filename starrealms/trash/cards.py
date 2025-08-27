# starrealms/cards.py

"""
Card definitions for the Star Realms Base Set (80 cards + Explorers).
Uses a structured dictionary of effects that are handled by effects.py.
"""

# Effect examples this schema expects:
# {"type": "trade", "amount": 2}
# {"type": "combat", "amount": 3}
# {"type": "draw", "amount": 1}
# {"type": "authority", "amount": 4}
# {"type": "discard", "amount": 1}                 # opponent discards 1 (as used elsewhere in your code)
# {"type": "scrap_hand_or_discard"}                # scrap from hand or discard
# {"type": "destroy_base"}                         # destroy a target base
# {"type": "destroy_target_trade_row"}             # scrap a card from trade row
# {"type": "choose", "options": [ [...], [...] ]}  # modal effects
# {"type": "ally_any_faction"}                     # Mech World
# {"type": "per_ship_combat", "amount": 1}         # Fleet HQ
# {"type": "topdeck_next_purchase"}                # Freighter/Blob Carrier

CARDS = [
    # --- TRADE FEDERATION ---
    {
        "name": "Federation Shuttle",
        "faction": "Federation",
        "type": "ship",
        "cost": 1,
        "effects": [{"type": "trade", "amount": 2}],
        "ally": [{"type": "authority", "amount": 4}],
    },
    {
        "name": "Cutter",
        "faction": "Federation",
        "type": "ship",
        "cost": 2,
        "effects": [{"type": "trade", "amount": 2}, {"type": "authority", "amount": 4}],
        "ally": [{"type": "combat", "amount": 4}],
    },
    {
        "name": "Embassy Yacht",
        "faction": "Federation",
        "type": "ship",
        "cost": 3,
        "effects": [{"type": "authority", "amount": 3}, {"type": "trade", "amount": 2}],
        "conditional": {
            "require_bases": 2,
            "effects": [{"type": "draw", "amount": 1}],
        },
    },
    {
        "name": "Freighter",
        "faction": "Federation",
        "type": "ship",
        "cost": 4,
        "effects": [{"type": "trade", "amount": 4}],
        "ally": [{"type": "topdeck_next_purchase"}],
    },
    {
        "name": "Trade Escort",
        "faction": "Federation",
        "type": "ship",
        "cost": 5,
        "effects": [{"type": "trade", "amount": 3}, {"type": "authority", "amount": 4}],
        "ally": [{"type": "combat", "amount": 4}],
    },
    {
        "name": "Flagship",  # moved to correct faction; restored ally authority
        "faction": "Federation",
        "type": "ship",
        "cost": 6,
        "effects": [{"type": "combat", "amount": 5}, {"type": "draw", "amount": 1}],
        "ally": [{"type": "authority", "amount": 5}],
    },
    {
        "name": "Command Ship",
        "faction": "Federation",
        "type": "ship",
        "cost": 8,
        "effects": [
            {"type": "authority", "amount": 4},
            {"type": "combat", "amount": 5},
            {"type": "draw", "amount": 2},
        ],
    },
    {
        "name": "Trading Post",
        "faction": "Federation",
        "type": "base",
        "cost": 3,
        "defense": 4,
        "outpost": True,
        "effects": [{"type": "trade", "amount": 1}],
        "choice": [{"type": "authority", "amount": 1}, {"type": "combat", "amount": 1}],
        "scrap": [{"type": "trade", "amount": 3}],
    },
    {
        "name": "Barter World",
        "faction": "Federation",
        "type": "base",
        "cost": 4,
        "defense": 4,
        "effects": [{"type": "trade", "amount": 2}, {"type": "authority", "amount": 2}],
        "scrap": [{"type": "draw", "amount": 1}],
    },
    {
        "name": "Defense Center",
        "faction": "Federation",
        "type": "base",
        "cost": 5,
        "defense": 5,
        "outpost": True,
        "effects": [{"type": "combat", "amount": 2}],
        "choice": [{"type": "authority", "amount": 3}, {"type": "combat", "amount": 2}],
    },
    {
        "name": "Port of Call",
        "faction": "Federation",
        "type": "base",
        "cost": 6,
        "defense": 6,
        "outpost": True,
        "effects": [{"type": "trade", "amount": 3}],
        "scrap": [{"type": "draw", "amount": 2}, {"type": "destroy_base"}],
    },
    {
        "name": "Central Office",
        "faction": "Federation",
        "type": "base",
        "cost": 7,
        "defense": 6,
        "effects": [{"type": "trade", "amount": 2}],
        "ally": [{"type": "draw", "amount": 1}],
        "scrap": [{"type": "topdeck_next_purchase"}],
    },

    # --- BLOB ---
    {
        "name": "Blob Fighter",
        "faction": "Blob",
        "type": "ship",
        "cost": 1,
        "effects": [{"type": "combat", "amount": 3}],
        "ally": [{"type": "draw", "amount": 1}],
    },
    {
        "name": "Battle Pod",
        "faction": "Blob",
        "type": "ship",
        "cost": 2,
        "effects": [{"type": "combat", "amount": 4}],
        "ally": [{"type": "destroy_target_trade_row"}],
    },
    {
        "name": "Trade Pod",  # added (was missing)
        "faction": "Blob",
        "type": "ship",
        "cost": 2,
        "effects": [{"type": "trade", "amount": 3}],
        "ally": [{"type": "combat", "amount": 2}],
    },
    {
        "name": "Ram",
        "faction": "Blob",
        "type": "ship",
        "cost": 3,
        "effects": [{"type": "combat", "amount": 5}],
        "ally": [{"type": "trade", "amount": 2}],
        "scrap": [{"type": "combat", "amount": 2}],
    },
    {
        "name": "Blob Wheel",  # fixed effects (trade +1; scrap: combat +3)
        "faction": "Blob",
        "type": "base",
        "cost": 3,
        "defense": 5,
        "effects": [{"type": "trade", "amount": 1}],
        "scrap": [{"type": "combat", "amount": 3}],
    },
    {
        "name": "Blob Destroyer",
        "faction": "Blob",
        "type": "ship",
        "cost": 4,
        "effects": [{"type": "combat", "amount": 6}],
        "ally": [{"type": "destroy_base"}, {"type": "destroy_target_trade_row"}],
    },
    {
        "name": "The Hive",
        "faction": "Blob",
        "type": "base",
        "cost": 5,
        "defense": 5,
        "effects": [{"type": "combat", "amount": 3}],
        "ally": [{"type": "draw", "amount": 1}],
    },
    {
        "name": "Blob Carrier",
        "faction": "Blob",
        "type": "ship",
        "cost": 6,
        "effects": [{"type": "combat", "amount": 7}],
        "ally": [{"type": "topdeck_next_purchase"}],
    },
    {
        "name": "Battle Blob",
        "faction": "Blob",
        "type": "ship",
        "cost": 6,
        "effects": [{"type": "combat", "amount": 8}],
        "ally": [{"type": "draw", "amount": 1}],
        "scrap": [{"type": "draw", "amount": 1}],
    },
    {
        "name": "Mothership",
        "faction": "Blob",
        "type": "ship",
        "cost": 7,
        "effects": [{"type": "combat", "amount": 6}, {"type": "draw", "amount": 1}],
        "ally": [{"type": "draw", "amount": 1}],
    },
    {
        "name": "Blob World",
        "faction": "Blob",
        "type": "base",
        "cost": 8,
        "defense": 7,
        "effects": [{"type": "combat", "amount": 5}],
        "ally": [{"type": "draw", "amount": 1}],
        "scrap": [{"type": "draw", "amount": 1}],
    },

    # --- MACHINE CULT ---
    {
        "name": "Trade Bot",
        "faction": "Machine Cult",
        "type": "ship",
        "cost": 1,
        "effects": [{"type": "trade", "amount": 1}, {"type": "scrap_hand_or_discard"}],
    },
    {
        "name": "Missile Bot",
        "faction": "Machine Cult",
        "type": "ship",
        "cost": 2,
        "effects": [{"type": "combat", "amount": 2}, {"type": "scrap_hand_or_discard"}],
    },
    {
        "name": "Supply Bot",
        "faction": "Machine Cult",
        "type": "ship",
        "cost": 3,
        "effects": [{"type": "trade", "amount": 2}, {"type": "scrap_hand_or_discard"}],
    },
    {
        "name": "Patrol Mech",
        "faction": "Machine Cult",
        "type": "ship",
        "cost": 4,
        "effects": [{"type": "choose", "options": [
            [{"type": "combat", "amount": 5}],
            [{"type": "trade", "amount": 3}],
        ]}],
        "ally": [{"type": "scrap_hand_or_discard"}],
    },
    {
        "name": "Stealth Needle",
        "faction": "Machine Cult",
        "type": "ship",
        "cost": 4,
        "effects": [{"type": "copy_target_ship"}],
    },
    {
        "name": "Battle Mech",
        "faction": "Machine Cult",
        "type": "ship",
        "cost": 5,
        "effects": [{"type": "combat", "amount": 4}, {"type": "draw", "amount": 1}],
        "ally": [{"type": "scrap_hand_or_discard"}],
    },
    {
        "name": "Missile Mech",
        "faction": "Machine Cult",
        "type": "ship",
        "cost": 6,
        "effects": [{"type": "combat", "amount": 6}],
        "ally": [{"type": "destroy_base"}],
        "scrap": [{"type": "draw", "amount": 2}],
    },
    {
        "name": "Battle Station",
        "faction": "Machine Cult",
        "type": "base",
        "cost": 3,
        "defense": 5,
        "outpost": True,
        "effects": [],
        "scrap": [{"type": "combat", "amount": 5}],
    },
    {
        "name": "Mech World",
        "faction": "Machine Cult",
        "type": "base",
        "cost": 5,
        "defense": 6,
        "effects": [{"type": "ally_any_faction"}],
    },
    {
        "name": "Junkyard",
        "faction": "Machine Cult",
        "type": "base",
        "cost": 6,
        "defense": 5,
        "outpost": True,  # Junkyard is an outpost
        "effects": [{"type": "scrap_hand_or_discard"}],
    },
    {
        "name": "Machine Base",
        "faction": "Machine Cult",
        "type": "base",
        "cost": 7,
        "defense": 6,
        "outpost": True,
        "effects": [{"type": "combat", "amount": 3}],
        "ally": [{"type": "scrap_hand_or_discard"}],
    },
    {
        "name": "Brain World",
        "faction": "Machine Cult",
        "type": "base",
        "cost": 8,
        "defense": 6,
        "outpost": True,
        "effects": [{"type": "scrap_multiple", "amount": 2}, {"type": "draw", "amount": 2}],
    },

    # --- STAR EMPIRE ---
    {
        "name": "Imperial Fighter",
        "faction": "Star Empire",
        "type": "ship",
        "cost": 1,
        "effects": [{"type": "combat", "amount": 2}],
        "ally": [{"type": "discard", "amount": 1}],
    },
    {
        "name": "Corvette",
        "faction": "Star Empire",
        "type": "ship",
        "cost": 2,
        "effects": [{"type": "combat", "amount": 1}, {"type": "draw", "amount": 1}],
    },
    {
        "name": "Survey Ship",
        "faction": "Star Empire",
        "type": "ship",
        "cost": 3,
        "effects": [{"type": "trade", "amount": 1}, {"type": "draw", "amount": 1}],
    },
    {
        "name": "Imperial Frigate",
        "faction": "Star Empire",
        "type": "ship",
        "cost": 3,
        "effects": [{"type": "combat", "amount": 4}],
        "ally": [{"type": "discard", "amount": 1}],
        "scrap": [{"type": "combat", "amount": 2}],
    },
    {
        "name": "Space Station",  # fixed to combat base with scrap trade
        "faction": "Star Empire",
        "type": "base",
        "cost": 4,
        "defense": 4,
        "outpost": True,
        "effects": [{"type": "combat", "amount": 2}],
        "ally": [{"type": "combat", "amount": 2}],
        "scrap": [{"type": "trade", "amount": 4}],
    },
    {
        "name": "Recycling Station",  # fixed choose: discard 2 & draw 2 OR trade 1
        "faction": "Star Empire",
        "type": "base",
        "cost": 4,
        "defense": 4,
        "effects": [{"type": "choose", "options": [
            [{"type": "discard", "amount": 2}, {"type": "draw", "amount": 2}],
            [{"type": "trade", "amount": 1}],
        ]}],
    },
    {
        "name": "War World",  # ally should be extra combat (not discard)
        "faction": "Star Empire",
        "type": "base",
        "cost": 5,
        "defense": 4,
        "outpost": True,
        "effects": [{"type": "combat", "amount": 3}],
        "ally": [{"type": "combat", "amount": 2}],
    },
    {
        "name": "Royal Redoubt",  # added (missing)
        "faction": "Star Empire",
        "type": "base",
        "cost": 6,
        "defense": 6,
        "outpost": True,
        "effects": [{"type": "combat", "amount": 3}],
        "ally": [{"type": "combat", "amount": 2}, {"type": "discard", "amount": 1}],
    },
    {
        "name": "Battlecruiser",
        "faction": "Star Empire",
        "type": "ship",
        "cost": 6,
        "effects": [{"type": "combat", "amount": 5}, {"type": "draw", "amount": 1}],
        "ally": [{"type": "discard", "amount": 1}],
        "scrap": [{"type": "draw", "amount": 1}],
    },
    {
        "name": "Dreadnaught",
        "faction": "Star Empire",
        "type": "ship",
        "cost": 7,
        "effects": [{"type": "combat", "amount": 7}, {"type": "draw", "amount": 1}],
        "scrap": [{"type": "combat", "amount": 5}],
    },
    {
        "name": "Fleet HQ",
        "faction": "Star Empire",
        "type": "base",
        "cost": 8,
        "defense": 8,
        "effects": [{"type": "per_ship_combat", "amount": 1}],
    },

    # --- NEUTRAL / STARTERS ---
    {
        "name": "Explorer",
        "faction": "Neutral",
        "type": "ship",
        "cost": 2,
        "effects": [{"type": "trade", "amount": 2}],
        "scrap": [{"type": "combat", "amount": 2}],
    },
    {
        "name": "Scout",
        "faction": "Neutral",
        "type": "ship",
        "cost": 0,
        "starter": True,
        "effects": [{"type": "trade", "amount": 1}],
    },
    {
        "name": "Viper",
        "faction": "Neutral",
        "type": "ship",
        "cost": 0,
        "starter": True,
        "effects": [{"type": "combat", "amount": 1}],
    },
]


# Helper: fetch card by name
def get_card(name: str) -> dict:
    for card in CARDS:
        if card["name"].lower() == name.lower():
            return card
    raise ValueError(f"Card '{name}' not found in card library.")
    
    # -----------------------------
# Base Set distribution (80 cards)
# Counts apply only to TRADE DECK cards (not starters, not Explorer).
# -----------------------------
COUNTS = {
    # Trade Federation (20)
    "Federation Shuttle": 3,
    "Cutter": 3,
    "Embassy Yacht": 2,
    "Freighter": 2,
    "Trade Escort": 1,
    "Flagship": 1,
    "Command Ship": 1,
    "Trading Post": 2,
    "Barter World": 2,
    "Defense Center": 1,
    "Central Office": 1,
    "Port of Call": 1,

    # Blob (20)
    "Blob Fighter": 3,
    "Trade Pod": 3,
    "Battle Pod": 2,
    "Ram": 2,
    "Blob Destroyer": 2,
    "Battle Blob": 1,
    "Blob Carrier": 1,
    "Mothership": 1,
    "Blob Wheel": 3,
    "The Hive": 1,
    "Blob World": 1,

    # Star Empire (20)
    "Imperial Fighter": 3,
    "Imperial Frigate": 3,
    "Survey Ship": 3,
    "Corvette": 2,
    "Battlecruiser": 1,
    "Dreadnaught": 1,
    "Space Station": 2,
    "Recycling Station": 2,
    "War World": 1,
    "Royal Redoubt": 1,
    "Fleet HQ": 1,

    # Machine Cult (20)
    "Trade Bot": 3,
    "Missile Bot": 3,
    "Supply Bot": 3,
    "Patrol Mech": 2,
    "Stealth Needle": 1,
    "Battle Mech": 1,
    "Missile Mech": 1,
    "Battle Station": 2,
    "Mech World": 1,
    "Brain World": 1,
    "Machine Base": 1,
    "Junkyard": 1,
}

# Explorers: there are 10 in the box, but we keep them in a separate infinite pile.
EXPLORER_NAME = "Explorer"

# -----------------------------
# Build a full 80-card trade deck from CARDS + COUNTS
# -----------------------------
def build_trade_deck():
    """Return a new list expanded to the full 80-card base-set trade deck."""
    by_name = {c["name"]: c for c in CARDS}

    deck = []
    for name, n in COUNTS.items():
        card_proto = by_name.get(name)
        if not card_proto:
            raise ValueError(f"Card '{name}' listed in COUNTS but not found in CARDS.")

        if card_proto.get("starter") or name == EXPLORER_NAME:
            continue

        for _ in range(n):
            deck.append(card_proto.copy())

    # Sanity checks
    assert all(not c.get("starter") and c["name"] != EXPLORER_NAME for c in deck), \
        "Trade deck should not contain starters or Explorer"
    if len(deck) != 80:
        raise AssertionError(f"Trade deck should be 80 cards, got {len(deck)}")

    return deck