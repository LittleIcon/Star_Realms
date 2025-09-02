# starrealms/game.py
"""
Game loop and state manager for Star Realms.
Handles players, trade row, turn order, and win conditions.
"""

import random
from .cards import CARDS, build_trade_deck, EXPLORER_NAME
from .player import Player, trigger_effects, collect_effects
from .effects import apply_effects

# Unified ability runner (data-driven cards)
from starrealms.engine.unified_dispatcher import GameAPI, AbilityDispatcher


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

        # Provide a simple card database for tests/utilities that search
        # across both deck and DB (e.g., get_card_by_name on trade_deck + card_db).
        # Using templates from CARDS is sufficient for lookup.
        self.card_db = list(CARDS)

        # Explorer template
        self.explorer_card = _card_template(EXPLORER_NAME)

        # Players
        self.players = []
        for name in player_names:
            starting_deck = _make_starting_deck()
            is_human = str(name).lower() in ("you", "player 1")
            self.players.append(Player(name, starting_deck, is_human=is_human))

        # Turn pointers
        self.turn = 0  # 0/1 index of current player
        self.turn_number = 0  # visible counter, increments at start_turn

        # Opening hands: P1 draws 3, P2 draws 5 (first-turn advantage mitigation)
        self.players[0].draw_cards(3)
        self.players[1].draw_cards(5)

        # Ability dispatcher wiring
        self.ui = getattr(self, "ui", None)
        self.api = GameAPI(self, self.ui)
        self.dispatcher = AbilityDispatcher(self.api)
        # Track cards played this turn (ships + bases)
        self._played_this_turn = {self.players[0].name: [], self.players[1].name: []}

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
                return (
                    self.opponent()
                    if player is self.current_player()
                    else self.current_player()
                )
        return None

    # --- ally resolution ---
    @staticmethod
    def _faction_of(card):
        return card.get("faction")

    def resolve_allies(self, player: Player):
        """
        Re-scan player's ships and bases in play.
        Trigger ally effects that have not yet fired and meet their min_allies threshold.
        Each card's ally can fire at most once per turn (flag reset for bases at start_turn).
        """
        p = player
        o = self.players[0] if p is self.players[1] else self.players[1]

        in_play_all = list(getattr(p, "in_play", [])) + list(getattr(p, "bases", []))

        def same_faction_others_count(card):
            f = card.get("faction")
            if not f:
                return 0
            cnt = 0
            for c in in_play_all:
                if c is card:
                    continue
                if c.get("faction") == f:
                    cnt += 1
            return cnt

        for card in in_play_all:
            rt = card.setdefault("_rt", {})
            if rt.get("ally_triggered"):
                continue

            # Gather ally effects (supports both new/legacy schemas via collect_effects)
            ally_effs = collect_effects(card, "ally")
            if not ally_effs:
                continue

            allies = same_faction_others_count(card)
            # Only apply those effects that meet their threshold
            to_apply = [e for e in ally_effs if int(e.get("min_allies", 1)) <= allies]
            if not to_apply:
                continue

            apply_effects(to_apply, p, o, self)
            rt["ally_triggered"] = True
            self.log.append(
                f"{p.name} — Ally triggered on {card.get('name','?')} (allies={allies})"
            )

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
            b.setdefault("_rt", {})["ally_triggered"] = False

        # Trigger 'start_of_turn' effects on the active player's bases
        for b in p.bases:
            trigger_effects(b, "start_of_turn", p, o, self)

        # Unified on_turn_start abilities (data-driven schema)
        self.dispatcher.on_turn_start(p.name)
        # Reset played-this-turn tracking for the active player
        self._played_this_turn[p.name].clear()

    def end_turn(self):
        """Clean up active player's board and pass turn to the opponent."""
        self.current_player().end_turn()
        self.turn += 1
        self.refill_trade_row()

    # --- purchases ---
    def _acquire(self, player: "Player", card: dict):
        card_copy = card.copy()
        if getattr(player, "topdeck_next_purchase", False):
            player.deck.insert(0, card_copy)  # top of deck for pop(0)
            player.topdeck_next_purchase = False
            self.log.append(f"{player.name} gains {card_copy['name']} → top-deck")
        else:
            player.discard_pile.append(card_copy)
            self.log.append(f"{player.name} gains {card_copy['name']} → discard")

    def buy_explorer(self, player: "Player"):
        player.trade_pool -= 2
        self._acquire(player, self.explorer_card)
        self.log.append(f"{player.name} buys Explorer")

    # =========================
    # Adapter methods used by the unified dispatcher/GameAPI
    # =========================
    def _player_by_name(self, name: str) -> Player:
        for pl in self.players:
            if pl.name == name:
                return pl
        # Fallback to current player if unknown
        return self.current_player()

    # --- Pools / economy ---
    def add_trade(self, player_name: str, amount: int):
        p = self._player_by_name(player_name)
        p.trade_pool += amount
        self.log.append(f"{p.name} gains {amount} trade")

    def add_combat(self, player_name: str, amount: int):
        p = self._player_by_name(player_name)
        p.combat_pool += amount
        self.log.append(f"{p.name} gains {amount} combat")

    def add_authority(self, player_name: str, amount: int):
        p = self._player_by_name(player_name)
        p.authority += amount
        self.log.append(
            f"{p.name} {'gains' if amount>=0 else 'loses'} {abs(amount)} authority"
        )

    # --- Cards & zones ---
    def draw(self, player_name: str, n: int = 1):
        p = self._player_by_name(player_name)
        p.draw_cards(n)

    def force_discard(self, target: str, n: int = 1):
        # 'target' may be "opponent" or a specific player name
        p = self.opponent() if target == "opponent" else self._player_by_name(target)
        p.force_discard(n)

    def list_zone(self, player_name: str, zone: str):
        p = self._player_by_name(player_name)
        if zone == "hand":
            return p.hand
        if zone == "discard":
            return p.discard_pile
        if zone == "bases":
            return getattr(p, "bases", [])
        if zone == "in_play":
            return list(getattr(p, "in_play", [])) + list(getattr(p, "bases", []))
        if zone == "played_this_turn":
            return self._played_this_turn[p.name]
        if zone == "trade_row":
            return [c for c in self.trade_row if c]
        return []

    def scrap_card(self, player_name: str, zone: str, index: int):
        p = self._player_by_name(player_name)
        if zone == "hand":
            card = p.hand.pop(index)
        elif zone == "discard":
            card = p.discard_pile.pop(index)
        elif zone == "in_play":
            pool = getattr(p, "in_play", [])
            card = pool.pop(index)
        else:
            return
        self.scrap_heap.append(card)
        self.log.append(f"{p.name} scraps {card.get('name','?')}")

    # --- Market helpers ---
    def trade_row_filtered(self, filt: dict):
        def ok(c):
            if not c:
                return False
            for k, v in (filt or {}).items():
                if c.get(k) != v:
                    return False
            return True

        return [i for i, c in enumerate(self.trade_row) if ok(c)]

    def cost_of_trade_row(self, idx: int) -> int:
        c = self.trade_row[idx]
        return int(c.get("cost", 0)) if c else 0

    def spend_trade(self, player_name: str, cost: int):
        p = self._player_by_name(player_name)
        if p.trade_pool < cost:
            raise ValueError(f"Need {cost} trade; have {p.trade_pool}")
        p.trade_pool -= cost

    def acquire_from_trade_row(
            self, player_name: str, idx: int, destination: str = "discard"
        ):
            p = self._player_by_name(player_name)
            card = self.trade_row[idx]
            self.trade_row[idx] = None
            self.refill_trade_row()
            if destination == "discard":
                self._acquire(p, card)
            else:
                self._acquire_topdeck(p, card)

    def destroy_trade_row(self, idx: int):
        if self.trade_row[idx]:
            self.scrap_heap.append(self.trade_row[idx])
            self.trade_row[idx] = None
            self.refill_trade_row()

    # --- Bases / board ---
    def destroy_enemy_base(self, owner: str, base_idx: int):
        # owner will usually be "opponent" from abilities
        p = self.opponent() if owner == "opponent" else self._player_by_name(owner)
        if 0 <= base_idx < len(p.bases):
            base = p.bases.pop(base_idx)
            # tell dispatcher continuous effects are gone
            self.dispatcher.on_card_leave_play(p.name, base)
            self.scrap_heap.append(base)
            self.log.append(f"{p.name}'s base {base.get('name','?')} destroyed")

    def _acquire_topdeck(self, player: "Player", card: dict):
        player.deck.insert(0, card.copy())
        self.log.append(f"{player.name} gains {card['name']} → top-deck")

    # --- Tracking for Blob World / ally (used by dispatcher) ---
    def record_played_this_turn(self, player_name: str, card: dict):
        self._played_this_turn[player_name].append(card)
        
    # --- test/utility proxy to the global effect runner ---
    def apply_effects(self, effects, p1=None, p2=None, **kwargs):
        """
        Convenience wrapper so tests can do:
            g.apply_effects(effects, p1, p2, choice_index=0)
        Falls back to current player/opponent if p1/p2 not supplied.
        Forwards any extra keyword args to the global effects.apply_effects.
        """
        if p1 is None:
            p1 = self.current_player()
        if p2 is None:
            p2 = self.opponent()
        # Forward to module-level runner
        return apply_effects(effects, p1, p2, self, **kwargs)
    def _check_lethal(self):
        """Mark game over if any player's authority <= 0.
        Sets self.over/is_over and stores winner as a *name string*.
        """
        players = getattr(self, 'players', [])
        for p in players:
            if getattr(p, 'authority', 1) <= 0:
                # flags
                self.over = True
                self.is_over = True
                # winner as string
                winner_obj = next(pl for pl in players if pl is not p)
                self.winner = getattr(winner_obj, 'name', str(winner_obj))
                # log
                if hasattr(self, 'log'):
                    self.log.append(
                        f"{getattr(p, 'name', 'Opponent')} has been defeated! {self.winner} wins!"
                    )
                return
    def spend_combat_to_face(self, attacker, defender, amount):
        """Spend up to `amount` combat from `attacker` to damage `defender`'s authority,
        then check for lethal. Clamps to available combat and non-negative spend.
        """
        spend = int(amount or 0)
        if spend <= 0:
            return
        if spend > getattr(attacker, "combat_pool", 0):
            spend = attacker.combat_pool
        attacker.combat_pool -= spend
        defender.authority -= spend
        # lethal check
        if hasattr(self, "_check_lethal"):
            self._check_lethal()
        # optional log
        if hasattr(self, "log"):
            self.log.append(f"{attacker.name} deals {spend} damage to {defender.name}")
