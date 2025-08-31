# starrealms/ai.py
"""
Lightweight AI policy and trainer for Star Realms.

- PolicyAgent: simple policy that (by default) uses a 'replan' buy step.
- GoodHeuristicAgent: stronger hard-coded AI that plans buys directly (no 'replan').
- ai_take_turn: helper if you want to drive AI without the UI.
- train: optional random-search trainer that tweaks weights.
"""

from __future__ import annotations
import json
import os
import random
from typing import Dict, List, Tuple, Optional

# ---------------- Storage ----------------
AI_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "ai_data")
WEIGHTS_PATH = os.path.join(AI_DATA_DIR, "ai_weights.json")
os.makedirs(AI_DATA_DIR, exist_ok=True)

# ---------------- Default scoring weights ----------------
DEFAULT_WEIGHTS: Dict[str, float] = {
    "trade": 1.0,
    "combat": 1.0,
    "draw": 2.0,
    "authority": 0.4,
    "discard": 1.2,
    "scrap_hand_or_discard": 1.0,
    "scrap_multiple": 1.6,
    "destroy_base": 1.5,
    "destroy_target_trade_row": 0.5,
    "ally_any_faction": 0.6,
    "per_ship_combat": 0.8,
    "topdeck_next_purchase": 1.2,
    "copy_target_ship": 1.0,
    "base_defense": 0.15,
    "outpost_bonus": 0.6,
    "cost_penalty": 0.05,
}


# ---------------- Weights IO ----------------
def load_weights(path: str = WEIGHTS_PATH) -> Dict[str, float]:
    if os.path.exists(path):
        with open(path, "r") as f:
            disk = json.load(f)
        w = DEFAULT_WEIGHTS.copy()
        w.update(disk)
        return w
    return DEFAULT_WEIGHTS.copy()


def save_weights(weights: Dict[str, float], path: str = WEIGHTS_PATH) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(weights, f, indent=2, sort_keys=True)


# ---------------- Scoring helpers ----------------
def _sum_effects_for(card: dict, key: str) -> float:
    total = 0.0
    # Support both your new schema (on_play/activated/ally/scrap/passive)
    # and the older "effects" list.
    for section in ("on_play", "activated", "ally", "scrap", "effects", "passive"):
        effs = card.get(section, [])
        if not effs:
            continue
        seq = effs if isinstance(effs, list) else [effs]
        for e in seq:
            if not isinstance(e, dict):
                continue
            # activated could be "start_of_turn" wrappers e.g. {type:"start_of_turn", effect:{...}}
            if section == "activated" and e.get("type") == "start_of_turn":
                ee = e.get("effect")
                if isinstance(ee, dict) and ee.get("type") == key:
                    total += float(ee.get("amount", 0) or 0)
            # normal effect
            if e.get("type") == key:
                total += float(e.get("amount", 0) or 0)
            # choices
            if e.get("type") == "choose":
                opt_vals = []
                for opt in e.get("options", []):
                    opt_list = opt if isinstance(opt, list) else [opt]
                    v = 0.0
                    for ee in opt_list:
                        if isinstance(ee, dict) and ee.get("type") == key:
                            v += float(ee.get("amount", 0) or 0)
                    opt_vals.append(v)
                if opt_vals:
                    total += sum(opt_vals) / len(opt_vals)
    return total


def score_card(card: dict, weights: Dict[str, float]) -> float:
    s = 0.0
    for k in (
        "trade",
        "combat",
        "draw",
        "authority",
        "discard",
        "scrap_hand_or_discard",
        "scrap_multiple",
        "destroy_base",
        "destroy_target_trade_row",
        "ally_any_faction",
        "per_ship_combat",
        "topdeck_next_purchase",
        "copy_target_ship",
    ):
        s += _sum_effects_for(card, k) * weights.get(k, 0.0)

    if card.get("type") in ("base", "outpost"):
        s += (card.get("defense", 0) or 0) * weights.get("base_defense", 0.0)
        if card.get("outpost"):
            s += weights.get("outpost_bonus", 0.0)

    s -= (card.get("cost", 0) or 0) * weights.get("cost_penalty", 0.0)
    return s


# ---------------- Simple policy agent (uses 'replan') ----------------
class PolicyAgent:
    """Plans (cmd, arg) steps. Replans buys after 'pa' using a 'replan' marker."""

    def __init__(self, weights: Optional[Dict[str, float]] = None):
        self.weights = weights or load_weights()

    def _best_affordable_slot(self, game, player) -> Optional[int]:
        best_slot = None
        best_score = -1e18
        for i, card in enumerate(game.trade_row, start=1):
            if not card:
                continue
            if card["cost"] <= player.trade_pool:
                sc = score_card(card, self.weights)
                if sc > best_score:
                    best_score = sc
                    best_slot = i
        return best_slot

    def plan_turn(self, game) -> List[Tuple[str, object]]:
        # UI must handle 'replan' by performing buys
        return [("pa", None), ("replan", None), ("a", None), ("e", None)]


# ---------------- Stronger hard-coded AI (no 'replan') ----------------
class GoodHeuristicAgent(PolicyAgent):
    """Deterministic AI that plays, buys (twice), attacks, ends — no 'replan' step."""

    def __init__(self):
        weights = {
            "trade": 1.2,
            "combat": 1.0,
            "draw": 2.6,
            "authority": 0.35,
            "discard": 1.4,
            "scrap_hand_or_discard": 1.2,
            "scrap_multiple": 1.8,
            "destroy_base": 1.7,
            "destroy_target_trade_row": 0.6,
            "ally_any_faction": 0.7,
            "per_ship_combat": 0.9,
            "topdeck_next_purchase": 1.3,
            "copy_target_ship": 1.0,
            "base_defense": 0.18,
            "outpost_bonus": 0.7,
            "cost_penalty": 0.045,
        }
        super().__init__(weights=weights)

    def _best_affordable_slot(self, game, player):
        best_slot = None
        best_score = -1e9
        turn = getattr(game, "turn_number", 1)
        for i, card in enumerate(game.trade_row, start=1):
            if not card or card["cost"] > player.trade_pool:
                continue
            sc = score_card(card, self.weights)
            # Early bias: trade/draw; Mid bias: bases
            if turn <= 6:
                sc += 0.25 * _sum_effects_for(card, "trade")
                sc += 0.25 * _sum_effects_for(card, "draw")
            elif 6 < turn <= 12 and card.get("type") in ("base", "outpost"):
                sc += 0.6
            if sc > best_score:
                best_score, best_slot = sc, i
        return best_slot

    def plan_turn(self, game):
        p = game.current_player()
        cmds: List[Tuple[str, object]] = []

        # 1) Play all
        cmds.append(("pa", None))

        # 2) Try to scrap Explorers if we have very low combat (optional)
        try:
            if getattr(p, "combat_pool", 0) < 2:
                for idx, c in enumerate(getattr(p, "in_play", []), start=1):
                    if c and c.get("name") == "Explorer":
                        cmds.append(("u", ("ship", idx, "scrap")))
        except Exception:
            pass

        # 3) Buy up to two times
        for _ in range(2):
            slot = self._best_affordable_slot(game, p)
            if slot is not None:
                cmds.append(("b", slot))  # 1-based index
            elif p.trade_pool >= 2:
                cmds.append(("b", "x"))  # Explorer
            else:
                break

        # 4) Attack
        cmds.append(("a", None))

        # 5) End
        cmds.append(("e", None))
        return cmds


# ---------------- Drive AI via commands (optional helper) ----------------
def ai_take_turn(game, apply_command) -> None:
    agent = PolicyAgent()
    script = agent.plan_turn(game)
    i = 0
    while i < len(script):
        cmd, arg = script[i]
        if cmd == "replan":
            p = game.current_player()
            buys_done = 0
            while buys_done < 2:
                # best slot?
                slot = agent._best_affordable_slot(game, p)
                if slot is not None:
                    apply_command("b", str(slot))
                    buys_done += 1
                    continue
                # else Explorer
                if p.trade_pool >= 2:
                    apply_command("b", "x")
                    buys_done += 1
                    continue
                break
            i += 1
            continue

        apply_command(cmd, None if arg is None else str(arg))
        i += 1


# ---------------- Optional trainer API ----------------
def _mutate(weights: Dict[str, float], scale: float = 0.25) -> Dict[str, float]:
    nw = weights.copy()
    keys = list(nw.keys())
    n = max(3, len(keys) // 4)
    for k in random.sample(keys, n):
        jitter = random.uniform(-scale, scale)
        nw[k] = round(nw[k] + jitter, 4)
    return nw


def self_play_match(
    make_game, wA: Dict[str, float], wB: Dict[str, float], max_turns=200
) -> int:
    from starrealms.game import Game  # avoid circulars if you import this elsewhere

    game = make_game()
    turns = 0

    def _apply(cmd: str, arg: Optional[str]) -> None:
        p = game.current_player()
        o = game.opponent()
        if cmd == "pa":
            for card in list(p.hand):
                p.play_card(card, o, game)
        elif cmd == "b":
            if arg == "x":
                if p.trade_pool >= 2:
                    game.buy_explorer(p)
            else:
                idx = int(arg) - 1
                if 0 <= idx < len(game.trade_row):
                    card = game.trade_row[idx]
                    if card:
                        p.buy_card(card, game)
        elif cmd == "a":
            if p.combat_pool > 0:
                p.attack(o, game)
        elif cmd == "e":
            game.end_turn()

    agentA = PolicyAgent(wA)
    agentB = PolicyAgent(wB)

    while turns < max_turns:
        if game.check_winner():
            break
        # A
        for cmd, arg in agentA.plan_turn(game):
            if cmd == "replan":
                buys = 0
                while buys < 2:
                    slot = agentA._best_affordable_slot(game, game.current_player())
                    if slot is not None:
                        _apply("b", str(slot))
                        buys += 1
                    elif game.current_player().trade_pool >= 2:
                        _apply("b", "x")
                        buys += 1
                    else:
                        break
            else:
                _apply(cmd, None if arg is None else str(arg))
        winner = game.check_winner()
        if winner:
            return 1 if winner == game.players[0] else -1
        # B
        for cmd, arg in agentB.plan_turn(game):
            if cmd == "replan":
                buys = 0
                while buys < 2:
                    slot = agentB._best_affordable_slot(game, game.current_player())
                    if slot is not None:
                        _apply("b", str(slot))
                        buys += 1
                    elif game.current_player().trade_pool >= 2:
                        _apply("b", "x")
                        buys += 1
                    else:
                        break
            else:
                _apply(cmd, None if arg is None else str(arg))
        winner = game.check_winner()
        if winner:
            return 1 if winner == game.players[0] else -1
        turns += 1

    return -1


def train(
    make_game, iterations=20, matches_per_iter=20, log_fn=print
) -> Dict[str, float]:
    best = load_weights()
    for it in range(1, iterations + 1):
        candidate = _mutate(best, scale=0.25)
        wins = 0
        for _ in range(matches_per_iter):
            if random.random() < 0.5:
                res = self_play_match(make_game, candidate, best)
                wins += 1 if res == 1 else 0
            else:
                res = self_play_match(make_game, best, candidate)
                wins += 1 if res == -1 else 0
        score = wins / matches_per_iter
        log_fn(
            f"[iter {it}] candidate vs best: {wins}/{matches_per_iter} = {score:.2f}"
        )
        if score > 0.55:
            best = candidate
            save_weights(best)
            log_fn(f"  ✅ Updated weights saved to {WEIGHTS_PATH}")
    return best
