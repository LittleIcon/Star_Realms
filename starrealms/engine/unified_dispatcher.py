from __future__ import annotations
from typing import Any, Dict, List, Optional, Callable, Tuple

# ---------- GameAPI (adapter to your Game) ----------
class GameAPI:
    def __init__(self, game, ui):
        self.game = game
        self.ui = ui
        self.used_abilities: Dict[str, set[str]] = {}
        # hooks[player][event] -> List[(source_name, fn)]
        self.hooks: Dict[str, Dict[str, List[Tuple[str, Callable]]]] = {}

    # Turn lifecycle
    def start_turn(self, player: str):
        self.used_abilities.setdefault(player, set()).clear()

    # Pools
    def add_trade(self, player: str, amount: int):     self.game.add_trade(player, amount)
    def add_combat(self, player: str, amount: int):    self.game.add_combat(player, amount)
    def add_authority(self, player: str, amount: int): self.game.add_authority(player, amount)

    # Cards & zones
    def draw(self, player: str, n: int = 1):           [self.game.draw(player) for _ in range(n)]
    def force_discard(self, target: str, n: int = 1):  self.game.force_discard(target, n)
    def list_zone(self, player: str, zone: str) -> List[Dict[str, Any]]:
        return self.game.list_zone(player, zone)
    def scrap_card(self, player: str, zone: str, index: int): self.game.scrap_card(player, zone, index)

    # Market / board
    def trade_row_filtered(self, filt: Dict[str, Any]) -> List[int]: return self.game.trade_row_filtered(filt)
    def cost_of_trade_row(self, idx: int) -> int:      return self.game.cost_of_trade_row(idx)
    def spend_trade(self, player: str, cost: int):     self.game.spend_trade(player, cost)
    def acquire_from_trade_row(self, player: str, idx: int, destination: str): self.game.acquire_from_trade_row(player, idx, destination)
    def destroy_trade_row(self, idx: int):             self.game.destroy_trade_row(idx)
    def destroy_base(self, owner: str, base_idx: int): self.game.destroy_enemy_base(owner, base_idx)

    # Hooks (continuous)
    def register_hook(self, player: str, event: str, fn: Callable, source: str):
        p = self.hooks.setdefault(player, {})
        p.setdefault(event, []).append((source, fn))
    def unregister_hooks_from_source(self, player: str, source: str):
        for event, lst in self.hooks.get(player, {}).items():
            self.hooks[player][event] = [(s, fn) for (s, fn) in lst if s != source]
    def fire(self, player: str, event: str, **payload):
        for (_source, fn) in self.hooks.get(player, {}).get(event, []):
            fn(self, player, **payload)

    # Ally checks
    def faction_in_play(self, player: str, faction: str, min_count: int, scope: str) -> bool:
        zone = "played_this_turn" if scope == "this_turn" else "in_play"
        cards = self.list_zone(player, zone)
        return sum(1 for c in cards if c.get("faction") == faction) >= min_count

    # Once-per-turn tracking
    def mark_used(self, player: str, ability_id: str):
        self.used_abilities.setdefault(player, set()).add(ability_id)
    def can_use(self, player: str, ability_id: str) -> bool:
        return ability_id not in self.used_abilities.setdefault(player, set())


# ---------- Dispatcher ----------
class AbilityDispatcher:
    def __init__(self, api: GameAPI):
        self.api = api
        self.vars: Dict[str, Any] = {}  # ephemeral key/value between effects

    # Public hook points
    def on_card_enter_play(self, player: str, card: Dict[str, Any]):
        for ab in card.get("abilities", []):
            trig: str = ab.get("trigger", "")
            if trig.startswith("continuous:"):
                self._register_continuous(player, card, ab)
            elif trig == "on_play":
                if self._condition_ok(player, ab):
                    self._apply_effects(player, ab.get("effects", []))
        self._record_played_this_turn(player, card)

    def on_card_leave_play(self, player: str, card: Dict[str, Any]):
        self.api.unregister_hooks_from_source(player, card.get("name", f"id{card.get('id')}"))

    def on_turn_start(self, player: str):
        self.api.start_turn(player)
        for card in self.api.list_zone(player, "in_play"):
            for ab in card.get("abilities", []):
                if ab.get("trigger") == "on_turn_start" and self._condition_ok(player, ab):
                    self._apply_effects(player, ab.get("effects", []))

    def activate_card(self, player: str, card: Dict[str, Any], ability_id: Optional[str] = None):
        for ab in card.get("abilities", []):
            if ab.get("trigger") != "activated":
                continue
            if ability_id and ab.get("id") != ability_id:
                continue
            freq = ab.get("frequency", {})
            if freq.get("once_per_turn", True) and not self.api.can_use(player, ab.get("id")):
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
                return
        self._notify("No scrap-activated ability on this card.")

    def on_ship_played(self, player: str, ship_card: Dict[str, Any]):
        self.api.fire(player, "on_ship_played", ship=ship_card)

    # Internals
    def _condition_ok(self, player: str, ab: Dict[str, Any]) -> bool:
        cond = ab.get("condition")
        if not cond:
            return True
        if "faction_in_play" in cond:
            cfg = cond["faction_in_play"]
            return self.api.faction_in_play(player, cfg["faction"], int(cfg.get("min",1)), cfg.get("scope","this_turn"))
        return True

    def _register_continuous(self, player: str, card: Dict[str, Any], ab: Dict[str, Any]):
        trigger = ab.get("trigger")
        _, event = trigger.split(":", 1)
        source = card.get("name", f"id{card.get('id')}")
        effects = ab.get("effects", [])
        def hook_fn(api: GameAPI, p: str, **payload):
            self._apply_effects(p, effects)
        self.api.register_hook(player, event, hook_fn, source=source)

    def _record_played_this_turn(self, player: str, card: Dict[str, Any]):
        g = getattr(self.api, "game", None)
        if g and hasattr(g, "record_played_this_turn"):
            g.record_played_this_turn(player, card)

    def _notify(self, msg: str):
        ui = getattr(self.api, "ui", None)
        if ui and hasattr(ui, "notify"):
            ui.notify(msg)

    # Effects dispatcher
    def _apply_effects(self, player: str, effects: List[Dict[str, Any]]):
        for e in effects:
            t = e.get("type")
            if t == "trade":
                self.api.add_trade(player, int(e["amount"]))
            elif t == "combat":
                self.api.add_combat(player, int(e["amount"]))
            elif t == "authority":
                self.api.add_authority(player, int(e["amount"]))
            elif t == "draw":
                self.api.draw(player, int(e.get("amount", 1)))
            elif t == "discard":
                target = e.get("target", "opponent")
                self.api.force_discard(target, int(e["amount"]))

            elif t == "scrap_selected":
                max_n = int(e.get("max", 0))
                zones = e.get("zones", ["hand"])
                picks = self._pick_multi(player, zones, max_n)
                for (zone, idx, _card) in picks:
                    self.api.scrap_card(player, zone, idx)
                key = e.get("store_as")
                if key:
                    self.vars[key] = len(picks)

            elif t == "draw_from":
                key = e["key"]
                n = int(self.vars.get(key, 0))
                if n > 0:
                    self.api.draw(player, n)

            elif t == "count":
                where = e["where"]
                filt = e.get("filter", {})
                key  = e.get("store_as", "count")
                self.vars[key] = self._count(player, where, filt)

            elif t == "choose_one":
                labels = [opt.get("label", f"Option {i+1}") for i, opt in enumerate(e["options"])]
                pick = self._choose(labels)
                if pick is not None:
                    self._apply_effects(player, e["options"][pick].get("effects", []))

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

            elif t == "move":
                pass
            elif t == "ally_any_faction":
                pass
            else:
                self._notify(f"Unknown effect type: {t}")

    # UI helpers
    def _pick_multi(self, player: str, zones: List[str], max_count: int):
        ui = getattr(self.api, "ui", None)
        if ui and hasattr(ui, "pick_multi_cards"):
            return ui.pick_multi_cards(player=player, zones=zones, max_count=max_count, allow_less=True,
                                       prompt=f"Pick up to {max_count} (Enter to confirm): ")
        return []

    def _choose(self, labels: List[str]) -> Optional[int]:
        ui = getattr(self.api, "ui", None)
        if ui and hasattr(ui, "pick_from_labels"):
            return ui.pick_from_labels(labels, prompt="Choose one:")
        return 0 if labels else None

    def _pick_trade_row(self, filt: Optional[Dict[str, Any]]):
        ui = getattr(self.api, "ui", None)
        if ui and hasattr(ui, "pick_trade_row"):
            return ui.pick_trade_row(filter=filt)
        matches = self.api.trade_row_filtered(filt or {})
        return matches[0] if matches else None

    def _pick_enemy_base(self, enemy: str) -> Optional[int]:
        ui = getattr(self.api, "ui", None)
        if ui and hasattr(ui, "pick_enemy_base"):
            return ui.pick_enemy_base(owner=enemy)
        return None

    def _count(self, player: str, where: str, filt: Dict[str, Any]) -> int:
        cards = self.api.list_zone(player, where)
        def ok(c):
            for k, v in filt.items():
                if c.get(k) != v:
                    return False
            return True
        return sum(1 for c in cards if ok(c))
