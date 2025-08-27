# starrealms/game.py
"""
Game loop and state manager for Star Realms.
Handles players, trade row, turn order, and win conditions.
"""

import random
from .cards import CARDS, build_trade_deck, EXPLORER_NAME
from .player import Player, trigger_effects


def _card_template(name: str):
    return next(c for c in CARDS if c["name"] == name)


def _make_starting_deck():
    scouts = [_card_template("Scout").copy() for _ in range(8)]
    vipers = [_card_template("Viper").copy() for _ in range(2)]
    return scouts + vipers


class Game:
    def __init__(self, player_names=("Player 1", "Player 2")):
        self.log = []

        # Trade deck & row
        self.trade_deck = build_trade_deck()
        random.shuffle(self.trade_deck)
        self.trade_row = [self.trade_deck.pop() for _ in range(5)]  # 5 fixed slots
        self.scrap_heap = []

        # Explorer template
        self.explorer_card = _card_template(EXPLORER_NAME)

        # Players
        self.players = []
        for name in player_names:
            starting_deck = _make_starting_deck()
            is_human = (str(name).lower() in ("you", "player 1"))
            self.players.append(Player(name, starting_deck, is_human=is_human))

        # Turn pointers
        self.turn = 0            # 0/1 index of current player
        self.turn_number = 0     # visible counter, increments at start_turn

        # Opening hands: P1 draws 3, P2 draws 5 (first-turn advantage mitigation)
        self.players[0].draw_cards(3)
        self.players[1].draw_cards(5)

    # --- helpers ---
    def current_player(self) -> Player:
        return self.players[self.turn % 2]

    def opponent(self) -> Player:
        return self.players[(self.turn + 1) % 2]

    def refill_trade_row(self):
        """
        Fill only empty (None) trade-row slots from the trade deck; do not shift.
        Ensure we keep exactly 5 slots at all times.
        """
        # Keep exactly 5 slots
        while len(self.trade_row) < 5:
            self.trade_row.append(self.trade_deck.pop() if self.trade_deck else None)

        # Refill any empty slots in place
        for i in range(5):
            if self.trade_row[i] is None and self.trade_deck:
                self.trade_row[i] = self.trade_deck.pop()

    def check_winner(self):
        """
        If any player's authority is <= 0, the *other* player wins.
        Return the winning Player object or None if no winner yet.
        """
        for player in self.players:
            if player.authority <= 0:
                return self.opponent() if player is self.current_player() else self.current_player()
        return None

    # --- ally resolution (NEW) ---
    @staticmethod
    def _faction_of(card):
        return card.get("faction")

    def resolve_allies(self, player: Player):
        """
        Re-scan the player's ships and bases in play.
        Trigger any Ally effects that have not yet fired but now qualify.
        Only logs/triggers for cards that actually have ally effects.
        """
        p = player
        # Opponent of p (not necessarily the current_player/opponent pair)
        o = self.players[0] if p is self.players[1] else self.players[1]

        # Build the set we consider "in play" for ally checks
        in_play_all = list(getattr(p, "in_play", [])) + list(getattr(p, "bases", []))

        def faction_count(f):
            if not f:
                return 0
            return sum(1 for c in in_play_all if self._faction_of(c) == f)

        # helper: does card actually have ally effects?
        def _has_ally_effects(card):
            if isinstance(card.get("ally"), list) and card["ally"]:
                return True
            if isinstance(card.get("ally_effects"), list) and card["ally_effects"]:
                return True
            for e in (card.get("effects") or []):
                if isinstance(e, dict) and e.get("trigger") == "ally":
                    return True
            return False

        for card in in_play_all:
            rt = card.setdefault('_rt', {})
            if rt.get('ally_triggered'):
                continue

            f = self._faction_of(card)
            if not f:
                continue

            # Only consider cards that actually have ally text
            if not _has_ally_effects(card):
                continue

            # Star Realms ally condition: at least one *other* card of same faction
            if faction_count(f) >= 2:
                trigger_effects(card, "ally", p, o, self)
                rt['ally_triggered'] = True
                self.log.append(f"{p.name} — Ally triggered on {card.get('name', '?')}")

    def on_card_entered_play(self, player: Player):
        """
        Call this whenever a ship/base enters play (after its on_play effects resolve).
        This will re-check ally conditions for all cards in play and fire any pending allies.
        """
        self.resolve_allies(player)

    # --- flow ---
    def start_turn(self):
        """
        Start-of-turn bookkeeping and base effects for the current player.
        Turn number increments here so each player's turn advances the counter.
        """
        self.turn_number += 1
        p = self.current_player()
        o = self.opponent()

        # Log
        self.log.append(f"— Start of TURN {self.turn_number}: {p.name} —")

        # Reset ally flags for persistent bases so they can fire again this turn
        for b in p.bases:
            b.setdefault('_rt', {})['ally_triggered'] = False

        # Trigger 'start_of_turn' effects on the active player's bases
        for b in p.bases:
            trigger_effects(b, "start_of_turn", p, o, self)

    def end_turn(self):
        """Clean up active player's board and pass turn to the opponent."""
        self.current_player().end_turn()
        self.turn += 1
        self.refill_trade_row()

    # --- purchases ---
    def buy_explorer(self, player: Player):
        player.trade_pool -= 2
        player.discard_pile.append(self.explorer_card.copy())
        self.log.append(f"{player.name} buys Explorer")