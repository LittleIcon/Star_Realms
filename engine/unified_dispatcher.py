# starrealms/engine/unified_dispatcher.py
from __future__ import annotations
from typing import Any, Dict, List, Optional, Callable, Tuple


# ---------- GameAPI (shim) ----------
class GameAPI:
    """
    Adapter between the dispatcher and your concrete Game implementation.
    Replace pass-through methods with your game's actual functions if needed.
    """

    def __init__(self, game, ui):
        self.game = game
        self.ui = ui

        # used_abilities_this_turn[player] -> set of ability IDs
        self.used_abilities: Dict[str, set[str]] = {}

        # hooks[player]["on_ship_played"] -> List[Tuple[source_name, Callable]]
        self.hooks: Dict[str, Dict[str, List[Tuple[str, Callable]]]] = {}

        # Per-player "ally any faction" wildcard (e.g., Mech World) active source counter
        self._ally_wildcard_count: Dict[str, int] = {}

    # --- Turn lifecycle ---
    def start_turn(self, player: str):
        self.used_abilities.setdefault(player, set()).clear()

    # --- Economy / pools ---
    def add_trade(self, player: str, amount: int):
        self.game.add_trade(player, amount)

    def add_combat(self, player: str, amount: int):
        self.game.add_combat(player, amount)

    def add_authority(self, player: str, amount: int):
        self.game.add_authority(player, amount)

    # --- Cards & zones ---
    def draw(self, player: str, n: int = 1):
        for _ in range(n):
            self.game.draw(player)

    def force_discard(self, target: str, n: int = 1):
        self.game.force_discard(target, n)

    def list_zone(self, player: str, zone: str) -> List[Dict[str, Any]]:
        # zones: "hand", "discard", "in_play", "bases", "deck", "played_this_turn", "trade_row"
        return self.game.list_zone(player, zone)

    def scrap(self, player: str, zone: str, index: int):
        self.game.scrap_card(player, zone=zone, index=index)

    # --- Market / board ---
    def trade_row_filtered(self, filt: Dict[str, Any]) -> List[int]:
        return self.game.trade_row_filtered(filt)

    def cost_of_trade_row(self, idx: int) -> int:
        return self.game.cost_of_trade_row(idx)

    def spend_trade(self, player: str, cost: int):
        self.game.spend_trade(player, cost)

    def acquire_from_trade_row(self, player: str, idx: int, destination: str):
        self.game.acquire_from_trade_row(player, idx, destination)

    def destroy_trade_row(self, idx: int):
        self.game.destroy_trade_row(idx)

    def destroy_base(self, owner: str, base_idx: int):
        self.game.destroy_enemy_base(owner, base_idx)

    # --- Hooks (continuous) ---
    def register_hook(self, player: str, event: str, fn: Callable, source: str):
        p = self.hooks.setdefault(player, {})
        lst = p.setdefault(event, [])
        lst.append((source, fn))

    def unregister_hooks_from_source(self, player: str, source: str):
        for event, lst in self.hooks.get(player, {}).items():
            self.hooks[player][event] = [(s, fn) for (s, fn) in lst if s != source]

    def fire(self, player: str, event: str, **payload):
        for (_source, fn) in self.hooks.get(player, {}).get(event, []):
            fn(self, player, **payload)

    # --- Ally wildcard helpers (NEW) ---
    def _bump_ally_wildcard(self, player: str, delta: int):
        c = self._ally_wildcard_count.get(player, 0) + delta
        if c < 0:
            c = 0
        self._ally_wildcard_count[player] = c

    def ally_wildcard_active(self, player: str) -> bool:
        return self._ally_wildcard_count.get(player, 0) > 0

    # --- Ally conditions ---
    def faction_in_play(self, player: str, faction: str, min_count: int, scope: str) -> bool:
        """
        True if the player effectively has an ally of `faction` in the requested scope.
        If a wildcard (Mech World) is active, short-circuit to True.
        """
        if self.ally_wildcard_active(player):
            return True

        zone = "played_this_turn" if scope == "this_turn" else "in_play"
        cards = self.list_zone(player, zone)

        def _match(c):
            fac = c.get("faction")
            if isinstance(fac, str):
                return fac == faction
            if isinstance(fac, (list, tuple, set)):
                return faction in fac
            return False

        return sum(1 for c in cards if _match(c)) >= min_count

    # --- Used/Once-per-turn ---
    def mark_used(self, player: str, ability_id: str):
        self.used_abilities.setdefault(player, set()).add(ability_id)

    def can_use(self, player: str, ability_id: str) -> bool:
        return ability_id not in self.used_abilities.setdefault(player, set())


# ---------- Dispatcher ----------
class AbilityDispatcher:
    """
    Central dispatcher for abilities. Knows how to:
      - register continuous hooks when a card enters play
      - evaluate conditions for abilities
      - apply lists of simple effects
      - maintain a per-turn "played_this_turn" view if the Game exposes it

    Abilities schema examples:
      {
        "trigger": "on_play" | "activated" | "scrap_activated" | "on_turn_start" |
                   "continuous:on_ship_played" | ...,
        "id": "unique-id-if-activated",
        "frequency": {"once_per_turn": true},
        "condition": {"faction_in_play": {"faction":"Blob","min":1,"scope":"this_turn"}},
        "effects": [{"type":"combat","amount":3}, ...]
      }

    Mech World support:
      - recognized if name == "Mech World"
      - OR an ability with trigger 'continuous:*' that includes effect {"type":"ally_any_faction"}
      - OR legacy effects[] entry with type 'ally_any_faction' and trigger None/'continuous'
      While active, all ally checks succeed for the owner.
    """

    def __init__(self, api: GameAPI):
        self.api = api
        self.vars: Dict[str, Any] = {}  # transient per-resolution key/value

    # ===== Public hook points you call from your game loop =====

    def on_card_enter_play(self, player: str, card: Dict[str, Any]):
        # Register continuous hooks; run on_play abilities
        for ab in card.get("abilities", []):
            trig: str = ab.get("trigger", "")
            if trig.startswith("continuous:"):
                self._register_continuous(player, card, ab)
            elif trig == "on_play":
                if self._condition_ok(player, ab):
                    self._apply_effects(player, ab.get("effects", []))

        # Enable Mech World-style ally wildcard while this card is in play
        if self._card_provides_ally_wildcard(card):
            self.api._bump_ally_wildcard(player, +1)

        # Record for allies/Blob World counting if Game exposes it
        self._record_played_this_turn(player, card)

    def on_card_leave_play(self, player: str, card: Dict[str, Any]):
        # remove any hooks registered by this card
        self.api.unregister_hooks_from_source(player, card.get("name", f"id{card.get('id')}"))
        # Disable ally wildcard if this was one of the sources
        if self._card_provides_ally_wildcard(card):
            self.api._bump_ally_wildcard(player, -1)

    def on_turn_start(self, player: str):
        self.api.start_turn(player)
        for card in self.api.list_zone(player, "in_play"):
            for ab in card.get("abilities", []):
                if ab.get("trigger") == "on_turn_start" and self._condition_ok(player, ab):
                    self._apply_effects(player, ab.get("effects", []))

    def activate_card(self, player: str, card: Dict[str, Any], ability_id: Optional[str] = None):
        # run first activated ability (or specific by id) if once/turn not used
        for ab in card.get("abilities", []):
            if ab.get("trigger") != "activated":
                continue
            if ability_id and ab.get("id") != ability_id:
                continue
            freq = ab.get("frequency", {})
            if freq.get("once_per_turn", True):
                if not self.api.can_use(player, ab.get("id")):
                    self._notify("Already used this ability this turn.")
                    return
            if self._condition_ok(player, ab):
                self._apply_effects(player, ab.get("effects", []))
                if freq.get("once_per_turn", True):
                    self.api.mark_used(player, ab.get("id"))
                return

        self._notify("No activatable ability found.")

    def scrap_activate(self, player: str, card: Dict[str, Any]):
        for ab in card.get("abilities", []):
            if ab.get("trigger") == "scrap_activated" and self._condition_ok(player, ab):
                self._apply_effects(player, ab.get("effects", []))
                # your game should now remove/scrap the card permanently
                return
        self._notify("No scrap-activated ability on this card.")

    # Call this from your ship-play path AFTER adding the ship to in_play.
    def on_ship_played(self, player: str, ship_card: Dict[str, Any]):
        self.api.fire(player, "on_ship_played", ship=ship_card)

    # ===== Internals =====

    def _condition_ok(self, player: str, ab: Dict[str, Any]) -> bool:
        cond = ab.get("condition")
        if not cond:
            return True
        # Example: {"faction_in_play":{"faction":"Blob","min":1,"scope":"this_turn"}}
        if "faction_in_play" in cond:
            cfg = cond["faction_in_play"]
            return self.api.faction_in_play(
                player,
                cfg["faction"],
                int(cfg.get("min", 1)),
                cfg.get("scope", "this_turn"),
            )
        # Extend with more condition kinds here
        return True

    def _register_continuous(self, player: str, card: Dict[str, Any], ab: Dict[str, Any]):
        # e.g. trigger == "continuous:on_ship_played"
        trigger = ab.get("trigger")
        _, event = trigger.split(":", 1)
        source = card.get("name", f"id{card.get('id')}")
        effects = ab.get("effects", [])

        def hook_fn(api: GameAPI, p: str, **payload):
            # payload contains event-specific fields (e.g., ship=...)
            # effects can ignore or use payload via future extensions
            self._apply_effects(p, effects)

        self.api.register_hook(player, event, hook_fn, source=source)

    def _record_played_this_turn(self, player: str, card: Dict[str, Any]):
        # If your Game supports it, mirror the play into a per-turn zone for ally checks.
        g = self.game_if_present()
        if hasattr(g, "record_played_this_turn"):
            g.record_played_this_turn(player, card)
        # Else: assume your Game already handles it when cards enter play

    def game_if_present(self):
        # convenience if you need direct access
        return getattr(self.api, "game", None)

    def _notify(self, msg: str):
        if hasattr(self.api, "ui") and hasattr(self.api.ui, "notify"):
            self.api.ui.notify(msg)

    def _card_provides_ally_wildcard(self, card: Dict[str, Any]) -> bool:
        """
        True if the card provides 'ally any faction' while in play.
        Recognizes:
          - name == "Mech World"
          - abilities with trigger starting with 'continuous' that include effect {"type":"ally_any_faction"}
          - legacy effects[] entry {"type":"ally_any_faction"} with trigger None/'continuous'
        """
        if card.get("name") == "Mech World":
            return True

        # abilities[]
        for ab in card.get("abilities", []) or []:
            trig = ab.get("trigger", "")
            if trig.startswith("continuous"):
                for eff in ab.get("effects", []) or []:
                    if isinstance(eff, dict) and eff.get("type") == "ally_any_faction":
                        return True

        # effects[] (legacy)
        for eff in card.get("effects", []) or []:
            if (
                isinstance(eff, dict)
                and eff.get("type") == "ally_any_faction"
                and eff.get("trigger") in (None, "continuous")
            ):
                return True

        return False

    # --------- Effects dispatcher ---------
    def _apply_effects(self, player: str, effects: List[Dict[str, Any]]):
        for e in effects:
            t = e.get("type")

            # Basic resources
            if t == "trade":
                self.api.add_trade(player, int(e["amount"]))

            elif t == "combat":
                self.api.add_combat(player, int(e["amount"]))

            elif t == "authority":
                self.api.add_authority(player, int(e["amount"]))

            # Cards
            elif t == "draw":
                self.api.draw(player, int(e.get("amount", 1)))

            elif t in ("discard", "opponent_discards"):
                target = e.get("target", "opponent")
                self.api.force_discard(target, int(e.get("amount", 1)))

            # Selection / scrap
            elif t == "scrap_selected":
                max_n = int(e.get("max", 0))
                zones = e.get("zones", ["hand"])
                picks = self._pick_multi(player, zones, max_n)
                for (zone, idx, _card) in picks:
                    self.api.scrap(player, zone, idx)
                key = e.get("store_as")
                if key:
                    self.vars[key] = len(picks)

            elif t == "draw_from":
                key = e["key"]
                n = int(self.vars.get(key, 0))
                if n > 0:
                    self.api.draw(player, n)

            # Counting
            elif t == "count":
                where = e["where"]
                filt = e.get("filter", {})
                key = e.get("store_as", "count")
                self.vars[key] = self._count(player, where, filt)

            # Choice containers
            elif t == "choose_one":
                labels = [opt.get("label", f"Option {i+1}") for i, opt in enumerate(e["options"])]
                pick = self._choose(labels)
                if pick is not None:
                    self._apply_effects(player, e["options"][pick].get("effects", []))

            # Market interactions
            elif t == "acquire_free":
                idx = self._pick_trade_row(e.get("filter"))
                if idx is not None:
                    dest = e.get("destination", "discard")
                    self.api.acquire_from_trade_row(player, idx, destination=dest)

            elif t == "destroy_trade_row":
                idx = self._pick_trade_row(e.get("filter"))
                if idx is not None:
                    self.api.destroy_trade_row(idx)

            elif t == "destroy_base":
                enemy = e.get("owner", "opponent")
                base_idx = self._pick_enemy_base(enemy)
                if base_idx is not None:
                    self.api.destroy_base(enemy, base_idx)

            # Movement (placeholder)
            elif t == "move":
                # generic move placeholder
                pass

            # Ally-any-faction is handled as a continuous aura via enter/leave play.
            elif t == "ally_any_faction":
                # No-op here by design; presence is detected by _card_provides_ally_wildcard.
                pass

            else:
                self._notify(f"Unknown effect type: {t}")

    # --------- Helpers for CLI/UI prompts ---------
    def _pick_multi(self, player: str, zones: List[str], max_count: int):
        if hasattr(self.api, "ui") and hasattr(self.api.ui, "pick_multi_cards"):
            return self.api.ui.pick_multi_cards(
                player=player,
                zones=zones,
                max_count=max_count,
                allow_less=True,
                prompt=f"Pick up to {max_count} (Enter to confirm): ",
            )
        # Fallback: pick none
        return []

    def _choose(self, labels: List[str]) -> Optional[int]:
        if hasattr(self.api, "ui") and hasattr(self.api.ui, "pick_from_labels"):
            return self.api.ui.pick_from_labels(labels, prompt="Choose one:")
        return 0 if labels else None

    def _pick_trade_row(self, filt: Optional[Dict[str, Any]]):
        if hasattr(self.api, "ui") and hasattr(self.api.ui, "pick_trade_row"):
            return self.api.ui.pick_trade_row(filter=filt)
        # Fallback: first matching index
        matches = self.api.trade_row_filtered(filt or {})
        return matches[0] if matches else None

    def _pick_enemy_base(self, enemy: str) -> Optional[int]:
        if hasattr(self.api, "ui") and hasattr(self.api.ui, "pick_enemy_base"):
            return self.api.ui.pick_enemy_base(owner=enemy)
        # Fallback: None (caller will no-op)
        return None

    def _count(self, player: str, where: str, filt: Dict[str, Any]) -> int:
        cards = self.api.list_zone(player, where)

        def ok(c):
            for k, v in filt.items():
                if c.get(k) != v:
                    return False
            return True

        return sum(1 for c in cards if ok(c))