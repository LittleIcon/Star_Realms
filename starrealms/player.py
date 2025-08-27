"""
Player logic for Star Realms.
Handles deck, hand, discard, bases, authority, trade, combat, and card play.
"""

import random
from typing import Any, Dict, List
from .effects import apply_effects


# ---------- Effect collection (NEW + legacy tolerant) ----------

def collect_effects(card: Dict[str, Any], phase: str) -> List[Dict[str, Any]]:
    """
    Return a flat list of effect dicts for a given phase.
    Supported phases: "play", "activated", "ally", "scrap", "passive", "start_of_turn".
    Works with:
      - NEW schema: on_play / activated / ally / scrap / passive
      - Legacy schema: effects[{"trigger": "...", ...}] (trigger may be missing; default to play)
    Also flattens activated start-of-turn wrappers:
      { "type": "start_of_turn", "effect": { ... } }
    """
    out: List[Dict[str, Any]] = []

    # --- NEW schema direct mapping ---
    key = {
        "play": "on_play",
        "activated": "activated",
        "ally": "ally",
        "scrap": "scrap",
        "passive": "passive",
    }.get(phase)

    if key and isinstance(card.get(key), list):
        out.extend(card[key])

    # "start_of_turn" is encoded under "activated" in new schema
    if phase == "start_of_turn":
        for eff in card.get("activated", []) or []:
            if not isinstance(eff, dict):
                continue
            if eff.get("type") == "start_of_turn":
                inner = eff.get("effect")
                if isinstance(inner, dict):
                    out.append(inner)

    # --- Legacy schema (effects[] with trigger; tolerate missing trigger=play) ---
    for eff in card.get("effects", []) or []:
        if not isinstance(eff, dict):
            continue
        trig = eff.get("trigger")
        if trig is None:
            # Default legacy entries without trigger to on-play
            if phase == "play":
                out.append({k: v for k, v in eff.items() if k != "trigger"})
        else:
            if phase == "play" and trig == "play":
                out.append({k: v for k, v in eff.items() if k != "trigger"})
            elif phase == "activated" and trig in ("activated", "activate"):
                out.append({k: v for k, v in eff.items() if k != "trigger"})
            elif phase == "ally" and trig == "ally":
                out.append({k: v for k, v in eff.items() if k != "trigger"})
            elif phase == "scrap" and trig == "scrap":
                out.append({k: v for k, v in eff.items() if k != "trigger"})
            elif phase == "passive" and trig == "static":
                out.append({k: v for k, v in eff.items() if k != "trigger"})
            elif phase == "start_of_turn" and trig == "start_of_turn":
                out.append({k: v for k, v in eff.items() if k != "trigger"})

    return out


def trigger_effects(card: Dict[str, Any], phase: str, player, opponent, game) -> None:
    """Collect effects for `phase` from `card` and apply them."""
    effs = collect_effects(card, phase)
    if effs:
        apply_effects(effs, player, opponent, game)


def _has_activate_ability(card: Dict[str, Any]) -> bool:
    """True if the card has any explicit activated or scrap ability (new or legacy schema)."""
    # New schema
    if any(True for _ in (card.get("activated") or [])):
        return True
    if any(True for _ in (card.get("scrap") or [])):
        return True
    # Legacy
    for e in card.get("effects", []) or []:
        if not isinstance(e, dict):
            continue
        if e.get("trigger") in ("activated", "activate", "scrap"):
            return True
    return False


# ---------- Tiny runtime helper ----------

def _ensure_rt(card: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ensure per-instance runtime flags exist on the card.
    We use this to mark ally triggers so each card's ally fires at most once per turn.
    (Bases get reset at start of the owner's turn in game.start_turn.)
    """
    rt = card.setdefault("_rt", {})
    rt.setdefault("ally_triggered", False)
    return rt


class Player:
    def __init__(self, name, starting_deck, is_human: bool = False):
        self.name = name
        self.human = bool(is_human)

        self.deck = starting_deck[:]
        random.shuffle(self.deck)

        self.hand: List[Dict[str, Any]] = []
        self.discard_pile: List[Dict[str, Any]] = []
        self.in_play: List[Dict[str, Any]] = []
        self.bases: List[Dict[str, Any]] = []
        self.scrap_heap: List[Dict[str, Any]] = []

        self.authority = 50
        self.trade_pool = 0
        self.combat_pool = 0

        self.topdeck_next_purchase = False

        # Per-turn modifiers
        self.per_ship_combat_bonus = 0

    # --------------------
    # Core Card Handling
    # --------------------
    def draw_card(self):
        """
        Draw one card. If the deck is empty, shuffle the discard pile
        into a new deck. Draw from the front (index 0) so top-deck inserts draw first.
        """
        if not self.deck:
            self.reshuffle_discard_into_deck()
        if self.deck:
            c = self.deck.pop(0)
            self.hand.append(c)
            return c
        return None

    def draw_cards(self, n: int):
        for _ in range(n):
            self.draw_card()

    def reshuffle_discard_into_deck(self):
        if self.discard_pile:
            random.shuffle(self.discard_pile)
            self.deck = self.discard_pile[:]
            self.discard_pile.clear()

    def play_card(self, card, opponent, game):
        """
        Play a card from hand to in_play or bases, applying on-play effects.
        Ally effects are resolved centrally by the game engine via game.on_card_entered_play().
        """
        if card not in self.hand:
            return False

        self.hand.remove(card)
        _ensure_rt(card)  # make sure runtime flags exist

        if card.get("type") in ("base", "outpost"):
            card["_used"] = False
            self.bases.append(card)
            # Some bases have on-play effects
            trigger_effects(card, "play", self, opponent, game)
            # Re-check allies for all cards now in play
            game.on_card_entered_play(self)
        else:
            self.in_play.append(card)
            # Ship on-play effects
            trigger_effects(card, "play", self, opponent, game)
            # Re-check allies for all cards now in play
            game.on_card_entered_play(self)

        return True

    # ---------- Using bases & ships (manual activations / scrap) ----------
    def activate_base(self, card, opponent, game, scrap: bool = False):
        """
        Activate a base’s once-per-turn ability or scrap ability.
        If scrap=True, fire scrap effects and remove base from play.
        Otherwise, fire activated effects if not already used this turn.
        """
        if card not in self.bases:
            return False

        if scrap:
            effs = collect_effects(card, "scrap")
            if not effs:
                return False
            apply_effects(effs, self, opponent, game)
            self.bases.remove(card)
            self.scrap_heap.append(card)
            game.log.append(f"{self.name} scraps {card['name']} for effect")
            return True

        # normal activation
        if card.get("_used"):
            return False
        effs = collect_effects(card, "activated")
        if not effs:
            return False
        apply_effects(effs, self, opponent, game)
        card["_used"] = True
        game.log.append(f"{self.name} activates {card['name']}")
        return True

    def activate_ship(self, card, opponent, game, scrap: bool = False):
        """
        Use a ship’s activated or scrap ability while it’s in play.
        Example: Explorer scrap for +2 combat.
        """
        if card not in self.in_play:
            return False

        if scrap:
            effs = collect_effects(card, "scrap")
            if not effs:
                return False
            apply_effects(effs, self, opponent, game)
            self.in_play.remove(card)
            self.scrap_heap.append(card)
            game.log.append(f"{self.name} scraps {card['name']} for effect")
            return True

        # If any ship ever gets an 'activated' (non-scrap) ability:
        effs = collect_effects(card, "activated")
        if effs:
            apply_effects(effs, self, opponent, game)
            game.log.append(f"{self.name} activates {card['name']}")
            return True
        return False

    def end_turn(self):
        """
        Cleanup:
        - Discard hand and in-play (bases remain).
        - Reset pools/flags/bonuses.
        - Draw 5 new cards.
        """
        if self.hand:
            self.discard_pile.extend(self.hand)
            self.hand.clear()
        if self.in_play:
            self.discard_pile.extend(self.in_play)
            self.in_play.clear()

        self.trade_pool = 0
        self.combat_pool = 0
        for b in self.bases:
            b["_used"] = False
            # Do NOT reset ally flags here; bases re-arm at start of owner's turn in Game.start_turn.

        if hasattr(self, "ally_wildcard_active"):
            delattr(self, "ally_wildcard_active")
        self.per_ship_combat_bonus = 0

        self.draw_cards(5)

    # --------------------
    # Purchases
    # --------------------
    def buy_card(self, card, game):
        """
        Buy a card from the trade row without shifting other slots.
        Replaces the purchased slot with the next card from the trade deck (or None).
        """
        if self.trade_pool < card["cost"]:
            return False

        self.trade_pool -= card["cost"]

        # Find exact slot
        try:
            idx = next(i for i, c in enumerate(game.trade_row) if c is card)
        except StopIteration:
            try:
                idx = game.trade_row.index(card)
            except ValueError:
                return False

        # Gain the purchased card
        if self.topdeck_next_purchase:
            self.deck.insert(0, card)
            self.topdeck_next_purchase = False
        else:
            self.discard_pile.append(card)

        # Replace slot in place
        game.trade_row[idx] = game.trade_deck.pop() if game.trade_deck else None
        return True

    # --------------------
    # Combat
    # --------------------
    def attack(self, opponent, game):
        dmg = self.combat_pool
        self.combat_pool = 0
        opponent.authority -= dmg
        game.log.append(f"{self.name} deals {dmg} damage to {opponent.name}")