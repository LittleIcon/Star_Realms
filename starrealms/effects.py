# starrealms/effects.py
"""
Effect engine for Star Realms.
- Accepts either a single effect dict OR a list of effect dicts.
- Robustly handles 'choose' where each option may be a dict or a list of dicts.
- Logs player actions to game.log so turns are visible.
"""

from starrealms.view import ui_common
import random
from .engine.resolver import can_handle as _resolver_can, apply_effect as _resolver_apply

# ---------------------------------------------------------------------
# Back-compat shims: allow tests to monkeypatch starrealms.effects.ui_input/ui_print
# or starrealms.view.ui_common.ui_input/ui_print.
# ---------------------------------------------------------------------
def ui_input(prompt: str = ""):
    return ui_common.ui_input(prompt)

def ui_print(*args, **kwargs):
    return ui_common.ui_print(*args, **kwargs)

# Effect types that must be handled here (with prompts), never delegated to resolver
_INTERACTIVE_EFFECTS = {
    "scrap_hand_or_discard",
    "scrap_multiple",
    "discard_then_draw",
    "discard_up_to_then_draw",
    "destroy_base",
    "destroy_target_trade_row",
    "scrap_from_trade_row",
    "copy_target_ship",
}

# ---------------- Utilities ----------------

def _log(game, msg: str) -> None:
    try:
        game.log.append(msg)
    except Exception:
        pass

def _fmt_eff(e):
    """Short, single-effect formatter for logs."""
    if not isinstance(e, dict):
        return str(e)
    t = e.get("type")
    a = e.get("amount")
    if t == "trade": return f"+{a} trade"
    if t == "combat": return f"+{a} combat"
    if t == "authority": return f"+{a} authority"
    if t == "draw": return f"draw {a}"
    if t in ("discard", "opponent_discards"): return f"opponent discards {a}"
    if t == "scrap_hand_or_discard": return "scrap 1 from hand/discard"
    if t == "scrap_multiple": return f"scrap {a} from hand/discard"
    if t == "destroy_base": return "destroy a base"
    if t == "destroy_target_trade_row": return "scrap from trade row"
    if t == "ally_any_faction": return "counts as all factions this turn"
    if t == "per_ship_combat": return f"+{a} combat per ship this turn"
    if t == "topdeck_next_purchase": return "top-deck next purchase"
    if t == "copy_target_ship": return "copy a ship you played"
    if t == "choose": return "choose one"
    if t == "discard_then_draw":
        return f"discard up to {a}, then draw that many"
    return t or str(e)

def _fmt_list(effs):
    parts = []
    for e in (effs if isinstance(effs, list) else [effs]):
        parts.append(_fmt_eff(e))
    return ", ".join(parts)

def _list_with_idx(cards):
    return ", ".join(f"{i+1}:{c.get('name','?')}" for i, c in enumerate(cards)) or "(empty)"

def _prompt_scrap_one_from_pile(pile_label: str, pile, player, game) -> bool:
    """
    Ask the user to pick a single card (1-based) from `pile`.
    Returns True if a card was scrapped, False otherwise.
    """
    if not pile:
        ui_print(f"🪫 Your {pile_label} is empty.")
        return False

    # Ensure a scrap heap (tests often check game.scrap_heap)
    if not hasattr(game, "scrap_heap"):
        game.scrap_heap = []

    while True:
        ui_print(f"{pile_label.capitalize():<7}: [{_list_with_idx(pile)}]")
        ans = ui_input(
            f"Pick a {pile_label[:-1]} to scrap (1-based), or 'x' to cancel: "
        ).strip().lower()
        if ans in ("x", ""):
            ui_print("↩️  Cancelled.")
            return False
        if ans.isdigit():
            idx = int(ans) - 1
            if 0 <= idx < len(pile):
                card = pile.pop(idx)
                game.scrap_heap.append(card)
                _log(game, f"{player.name} scraps {card.get('name','?')} from {pile_label}")
                ui_print(f"🗑️  Scrapped {card.get('name','?')}.")
                return True
        ui_print("❗ Invalid index, try again.")

def _collect_on_play_effects(card):
    """
    Pull just the on-play effects from either schema:
      - new: card['on_play'] as list
      - legacy: card['effects'] entries with trigger == 'play' OR missing trigger
    """
    out = []
    if isinstance(card.get("on_play"), list):
        out.extend(card["on_play"])
    for eff in card.get("effects", []) or []:
        if not isinstance(eff, dict):
            continue
        trig = eff.get("trigger")
        if trig is None or trig == "play":
            out.append({k: v for k, v in eff.items() if k != "trigger"})
    return out

# ---------------- Core runners ----------------

def apply_effects(effects, player, opponent, game):
    """
    Apply a sequence of effects.
    'effects' may be:
      - None
      - a single dict
      - a list of dicts (or nested lists)
    """
    if not effects:
        return
    if isinstance(effects, dict):
        apply_effect(effects, player, opponent, game)
        return
    if isinstance(effects, list):
        for eff in effects:
            apply_effect(eff, player, opponent, game)
        return
    # anything else: ignore

def apply_effect(effect, player, opponent, game):
    """
    Apply a single effect or a list of effects (recursively).
    """
    # If a list sneaks in, apply each item and return
    if isinstance(effect, list):
        for e in effect:
            apply_effect(e, player, opponent, game)
        return

    # Ignore non-dicts quietly
    if not isinstance(effect, dict):
        return

    etype = effect.get("type")

    # Delegate simple effects to resolver (keeps prompts/UI separate)
    if etype not in _INTERACTIVE_EFFECTS and _resolver_can(etype):
        _resolver_apply(game, player, opponent, effect)
        return

    amt = effect.get("amount")

    # -------------- branching / containers --------------
    if etype == "choose":
        options = effect.get("options", [])
        if not options:
            return

        # Auto-pick first option (wire UI later if needed)
        chosen = options[0]
        chosen_pretty = _fmt_list(chosen if isinstance(chosen, list) else [chosen])
        _log(game, f"{player.name} chooses option 1: {chosen_pretty}")

        if isinstance(chosen, dict):
            apply_effect(chosen, player, opponent, game)
        elif isinstance(chosen, list):
            for sub in chosen:
                apply_effect(sub, player, opponent, game)
        return

    # -------------- basic resources --------------
    if etype == "trade":
        player.trade_pool += int(amt or 0)
        _log(game, f"{player.name} gains +{int(amt or 0)} trade (pool={player.trade_pool})")
        return

    if etype == "combat":
        player.combat_pool += int(amt or 0)
        _log(game, f"{player.name} gains +{int(amt or 0)} combat (pool={player.combat_pool})")
        return

    if etype == "authority":
        player.authority += int(amt or 0)
        _log(game, f"{player.name} gains +{int(amt or 0)} authority (total={player.authority})")
        return

    if etype == "draw":
        n = int(amt or 0)
        for _ in range(n):
            player.draw_card()
        _log(game, f"{player.name} draws {n} card(s)")
        return

    # -------------- purchase helpers --------------
    if etype == "topdeck_next_purchase":
        player.topdeck_next_purchase = True
        _log(game, f"{player.name} will top-deck their next purchase")
        return

    # -------------- flags / auras --------------
    if etype == "ally_any_faction":
        setattr(player, "ally_wildcard_active", True)
        _log(game, f"{player.name} counts as all factions this turn")
        return

    if etype == "per_ship_combat":
        inc = int(amt or 0)
        if inc:
            current = getattr(player, "per_ship_combat_bonus", 0)
            setattr(player, "per_ship_combat_bonus", current + inc)
            _log(game, f"{player.name} gains +{inc} combat per ship this turn (total={current+inc})")
        return

    # -------------- opponent discard --------------
    if etype in ("discard", "opponent_discards"):
        n = int(amt or 1)
        for _ in range(n):
            if not opponent.hand:
                _log(game, f"{opponent.name} has no cards to discard")
                break

            if getattr(opponent, "human", False):
                # Human opponent MUST discard; no skipping.
                while True:
                    ui_print(f"{opponent.name}, choose a card to discard:")
                    for i, c in enumerate(opponent.hand, start=1):
                        ui_print(f"  {i}: {c.get('name','?')}")
                    ans = ui_input("Index (1-based): ").strip()
                    if ans.isdigit():
                        idx = int(ans) - 1
                        if 0 <= idx < len(opponent.hand):
                            card = opponent.hand.pop(idx)
                            opponent.discard_pile.append(card)
                            _log(game, f"{opponent.name} discards {card.get('name','?')}")
                            break
                    ui_print("❗ Invalid choice, try again.")
            else:
                # Simple AI strategy: discard the first card
                card = opponent.hand.pop(0)
                opponent.discard_pile.append(card)
                _log(game, f"{opponent.name} discards {card.get('name','?')}")
        return

    if etype == "scrap_hand_or_discard":
        # Ensure heaps exist
        if not hasattr(player, "scrap_heap"):
            player.scrap_heap = []
        if not hasattr(game, "scrap_heap"):
            game.scrap_heap = []

        can_h = bool(player.hand)
        can_d = bool(player.discard_pile)
        if not can_h and not can_d:
            _log(game, f"{player.name} has nothing to scrap")
            return

        agent = getattr(player, "agent", None)

        # --- Agent path (new-style API) ---
        if agent is not None and hasattr(agent, "choose_pile_for_scrap") and hasattr(agent, "choose_index"):
            # ask which pile; allow cancel (agent in this test won't cancel)
            src = agent.choose_pile_for_scrap(len(player.hand), len(player.discard_pile), allow_cancel=True)
            if src is None:
                _log(game, f"{player.name} chooses not to scrap")
                return

            src_norm = str(src).lower()
            if src_norm in ("d", "discard"):
                pile = player.discard_pile
                if not pile:
                    _log(game, "Agent chose discard but it is empty")
                    return
            elif src_norm in ("h", "hand"):
                pile = player.hand
                if not pile:
                    _log(game, "Agent chose hand but it is empty")
                    return
            else:
                _log(game, "Agent returned invalid pile for scrap")
                return

            # choose_index returns 0-based index here
            idx0 = agent.choose_index("Pick a card index (0-based): ", len(pile), allow_cancel=True)
            if not (isinstance(idx0, int) and 0 <= idx0 < len(pile)):
                _log(game, "Agent gave invalid index; cancelling scrap")
                return

            card = pile.pop(idx0)
            game.scrap_heap.append(card)  # agent path → game heap
            _log(game, f"{player.name} scraps {card.get('name','?')} from {'discard' if pile is player.discard_pile else 'hand'}")
            return

        # --- Agent path (legacy API seen elsewhere) ---
        if agent is not None and hasattr(agent, "choose_pile") and hasattr(agent, "choose_index"):
            src = agent.choose_pile(
                "Scrap from [h]and or [d]iscard? (x=skip) ",
                can_hand=can_h,
                can_discard=can_d,
                cancellable=True,
            )
            if src is None:
                _log(game, f"{player.name} chooses not to scrap")
                return

            pile = player.hand if src == "h" else player.discard_pile
            idx = agent.choose_index(
                f"Pick a card 1..{len(pile)} (x=cancel): ",
                options=[c.get("name","?") for c in pile],
                cancellable=True
            )
            if idx is None:
                _log(game, f"{player.name} cancels scrapping")
                return

            # legacy choose_index uses 1-based
            if isinstance(idx, int) and 1 <= idx <= len(pile):
                card = pile.pop(idx - 1)
                game.scrap_heap.append(card)  # agent path → game heap
                _log(game, f"{player.name} scraps {card.get('name','?')} from {'hand' if src=='h' else 'discard'}")
            return

        # --- Human path (UI) ---
        if getattr(player, "human", False):
            while True:
                h_ct, d_ct = len(player.hand), len(player.discard_pile)
                ui_print(f"Hand   : [{_list_with_idx(player.hand)}]")
                ui_print(f"Discard: [{_list_with_idx(player.discard_pile)}]")
                ans = ui_input("Scrap from [h]and or [d]iscard? (x=skip) ").strip().lower()

                if ans in ("x", "skip", ""):
                    ui_print("↩️  Skipped scrapping.")
                    return

                if ans.startswith("h"):
                    if h_ct == 0:
                        ui_print("🪫 Your hand is empty. Choose discard or press x to skip.")
                        continue
                    if _prompt_scrap_one_from_pile("hand", player.hand, player, game):
                        return

                elif ans.startswith("d"):
                    if d_ct == 0:
                        ui_print("🪫 Your discard is empty. Choose hand or press x to skip.")
                        continue
                    if _prompt_scrap_one_from_pile("discard", player.discard_pile, player, game):
                        return

                else:
                    ui_print("❗ Invalid choice. Type 'h', 'd', or 'x'.")
            return

        # --- Non-agent AI fallback: prefer discard; put into player.scrap_heap
        if player.discard_pile:
            card = player.discard_pile.pop(0)
            player.scrap_heap.append(card)  # AI (no agent) → player heap
            _log(game, f"{player.name} scraps {card.get('name','?')} from discard")
        elif player.hand:
            card = player.hand.pop(0)
            player.scrap_heap.append(card)
            _log(game, f"{player.name} scraps {card.get('name','?')} from hand")
        return

        # --- Human path (legacy UI): keep using game.scrap_heap
        if getattr(player, "human", False):
            while True:
                h_ct, d_ct = len(player.hand), len(player.discard_pile)
                ui_print(f"Hand   : [{_list_with_idx(player.hand)}]")
                ui_print(f"Discard: [{_list_with_idx(player.discard_pile)}]")
                ans = ui_input("Scrap from [h]and or [d]iscard? (x=skip) ").strip().lower()

                if ans in ("x", "skip", ""):
                    ui_print("↩️  Skipped scrapping.")
                    return

                if ans.startswith("h"):
                    if h_ct == 0:
                        ui_print("🪫 Your hand is empty. Choose discard or press x to skip.")
                        continue
                    if _prompt_scrap_one_from_pile("hand", player.hand, player, game):
                        return
                elif ans.startswith("d"):
                    if d_ct == 0:
                        ui_print("🪫 Your discard is empty. Choose hand or press x to skip.")
                        continue
                    if _prompt_scrap_one_from_pile("discard", player.discard_pile, player, game):
                        return
                else:
                    ui_print("❗ Invalid choice. Type 'h', 'd', or 'x'.")
            return

        # --- Non-agent AI fallback: prefer discard; put into player.scrap_heap
        if player.discard_pile:
            card = player.discard_pile.pop(0)
            player.scrap_heap.append(card)  # AI → player heap (test expects this)
            _log(game, f"{player.name} scraps {card.get('name','?')} from discard")
        elif player.hand:
            card = player.hand.pop(0)
            player.scrap_heap.append(card)
            _log(game, f"{player.name} scraps {card.get('name','?')} from hand")
        return

    # -------------- variable discard then draw --------------
    # -------------- variable discard then draw --------------
    if etype in ("discard_then_draw", "discard_up_to_then_draw"):
        max_discards = int(amt or 0)
        if max_discards <= 0:
            return

        agent = getattr(player, "agent", None)
        actual_discards = 0

        # --- Agent path(s) ---
        if agent is not None:
            k = min(max_discards, len(player.hand))
            idxs = None

            # Preferred: matches your test's API
            if hasattr(agent, "choose_cards_to_discard"):
                try:
                    idxs = agent.choose_cards_to_discard(player.hand, k) or []
                except TypeError:
                    idxs = agent.choose_cards_to_discard(player.hand, up_to_n=k) or []

            # Alternate API some agents might use
            elif hasattr(agent, "choose_indices"):
                names = [c.get("name", "?") for c in player.hand]
                idxs = agent.choose_indices(
                    prompt=f"Choose up to {k} cards to discard (0-based)",
                    count=k,
                    from_list=names,
                ) or []

            if idxs is not None:
                # Normalize while PRESERVING ORDER from the agent:
                seen = set()
                ordered_valid = []
                for i in idxs:
                    if isinstance(i, int) and 0 <= i < len(player.hand) and i not in seen:
                        ordered_valid.append(i)
                        seen.add(i)
                    if len(ordered_valid) >= k:
                        break

                # Copy chosen cards in the same order the agent provided
                chosen_cards = [player.hand[i] for i in ordered_valid]

                # Rebuild hand without chosen indices (no index-shift issues)
                idx_set = set(ordered_valid)
                player.hand[:] = [c for j, c in enumerate(player.hand) if j not in idx_set]

                # Move to discard in the SAME order as chosen
                for card in chosen_cards:
                    player.discard_pile.append(card)
                    _log(game, f"{player.name} discards {card.get('name','?')} (agent)")
                    actual_discards += 1

        # --- Human path ---
        elif getattr(player, "human", False):
            while actual_discards < max_discards and player.hand:
                ui_print(f"Your hand: [{_list_with_idx(player.hand)}]")
                ans = ui_input(
                    f"Discard a card? ({actual_discards}/{max_discards}) "
                    f"Type 1-based index, or 'x' to stop: "
                ).strip().lower()
                if ans in ("x", "stop", ""):
                    break
                if ans.isdigit():
                    idx = int(ans) - 1
                    if 0 <= idx < len(player.hand):
                        card = player.hand.pop(idx)
                        player.discard_pile.append(card)
                        _log(game, f"{player.name} discards {card.get('name','?')} (self)")
                        actual_discards += 1
                    else:
                        ui_print("❗ Invalid index.")
                else:
                    ui_print("❗ Enter a card index or 'x' to stop.")

        # --- Simple AI fallback ---
        else:
            while actual_discards < max_discards and player.hand:
                card = player.hand.pop(0)
                player.discard_pile.append(card)
                _log(game, f"{player.name} discards {card.get('name','?')} (auto)")
                actual_discards += 1

        # Draw the same number you discarded
        for _ in range(actual_discards):
            player.draw_card()
        if actual_discards:
            _log(game, f"{player.name} draws {actual_discards} card(s) after discarding")
        else:
            _log(game, f"{player.name} chose not to discard")
        return

    # -------------- scrap multiple --------------
    if etype == "scrap_multiple":
        # Ensure heaps exist
        if not hasattr(player, "scrap_heap"):
            player.scrap_heap = []
        if not hasattr(game, "scrap_heap"):
            game.scrap_heap = []

        n = int(amt or 0)
        if n <= 0:
            return
        if not player.hand and not player.discard_pile:
            return

        # Human path: UI helper scrapes into game.scrap_heap (legacy behavior)
        if getattr(player, "human", False):
            ui_print(
                f"🧹 Scrap {n} {'card' if n==1 else 'cards'} from your hand/discard. (x=finish early)"
            )
            scrapped = 0
            while scrapped < n and (player.hand or player.discard_pile):
                ui_print(f"Hand   : [{_list_with_idx(player.hand)}]")
                ui_print(f"Discard: [{_list_with_idx(player.discard_pile)}]")
                ans = ui_input("Choose pile [h/d] (or 'x' to stop scrapping): ").strip().lower()
                if ans in ("x", ""):
                    break
                if ans not in ("h", "d", "hand", "discard"):
                    ui_print("❗ Invalid choice. Type 'h', 'd', or 'x'.")
                    continue

                if ans.startswith("h"):
                    if not player.hand:
                        ui_print("🪫 Your hand is empty.")
                        continue
                    if _prompt_scrap_one_from_pile("hand", player.hand, player, game):
                        scrapped += 1
                else:
                    if not player.discard_pile:
                        ui_print("🪫 Your discard is empty.")
                        continue
                    if _prompt_scrap_one_from_pile("discard", player.discard_pile, player, game):
                        scrapped += 1

            if scrapped:
                _log(game, f"{player.name} scrapped {scrapped} card(s)")
            return

        # --- AI path: prefer discard, then hand; put into player.scrap_heap ---
        scrapped = 0
        for _ in range(n):
            if player.discard_pile:
                card = player.discard_pile.pop(0)
                player.scrap_heap.append(card)   # <-- change is here
                _log(game, f"{player.name} scraps {card.get('name','?')} from discard")
                scrapped += 1
            elif player.hand:
                card = player.hand.pop(0)
                player.scrap_heap.append(card)   # <-- and here
                _log(game, f"{player.name} scraps {card.get('name','?')} from hand")
                scrapped += 1
            else:
                break
        if scrapped:
            _log(game, f"{player.name} scrapped {scrapped} card(s)")
        return

    # -------------- board / market interaction --------------
    if etype == "destroy_base":
        bases = opponent.bases
        if not bases:
            _log(game, f"{player.name} tries to destroy a base, but none available")
            return

        # For messaging only
        ui_print(
            "Opponent bases:",
            [f"{i+1}:{b.get('name','?')}{' [Outpost]' if b.get('outpost') else ''}"
             for i, b in enumerate(bases)]
        )

        outposts_exist = any(b.get("outpost") for b in bases)
        agent = getattr(player, "agent", None)

        # ---- Agent path: pass FULL bases; enforce rule AFTER choice
        if agent is not None and hasattr(agent, "choose_base_to_destroy"):
            idx = agent.choose_base_to_destroy(bases)
            if not (isinstance(idx, int) and 0 <= idx < len(bases)):
                _log(game, "Invalid base choice; no base destroyed")
                return

            chosen = bases[idx]
            if outposts_exist and not chosen.get("outpost"):
                # Illegal choice: must destroy an outpost first → reject
                _log(game, "Outpost present; non-outpost choice rejected")
                return

            # Legal: remove and notify
            removed = bases.pop(idx)
            if hasattr(game, "dispatcher") and hasattr(game.dispatcher, "on_card_leave_play"):
                game.dispatcher.on_card_leave_play(opponent.name, removed)
            ui_print(f"Destroyed {removed.get('name','base')}.")
            _log(game, f"{player.name} destroys {opponent.name}'s {removed.get('name','base')}")
            return

        # ---- Human path: 1-based index; enforce outpost-first
        if getattr(player, "human", False):
            ans = ui_input("Choose base index to destroy (1-based): ").strip()
            try:
                idx1 = int(ans) - 1
                if not (0 <= idx1 < len(bases)):
                    raise ValueError
                chosen = bases[idx1]
                if outposts_exist and not chosen.get("outpost"):
                    ui_print("You must destroy an outpost first.")
                    return
            except ValueError:
                ui_print("Invalid choice.")
                return

            removed = bases.pop(idx1)
            if hasattr(game, "dispatcher") and hasattr(game.dispatcher, "on_card_leave_play"):
                game.dispatcher.on_card_leave_play(opponent.name, removed)
            ui_print(f"Destroyed {removed.get('name','base')}.")
            _log(game, f"{player.name} destroys {opponent.name}'s {removed.get('name','base')}")
            return

        # ---- Auto path: if any outposts exist, destroy the first outpost; else first base
        if outposts_exist:
            for i, b in enumerate(bases):
                if b.get("outpost"):
                    removed = bases.pop(i)
                    break
        else:
            removed = bases.pop(0)

        if removed and hasattr(game, "dispatcher") and hasattr(game.dispatcher, "on_card_leave_play"):
            game.dispatcher.on_card_leave_play(opponent.name, removed)
        ui_print(f"Destroyed {removed.get('name','base')}.")
        _log(game, f"{player.name} destroys {opponent.name}'s {removed.get('name','base')}")
        return

    if etype in ("destroy_target_trade_row", "scrap_from_trade_row"):
        # Scrap a card from the trade row; always push to game.scrap_heap and refill.
        if not getattr(game, "trade_row", None):
            _log(game, f"{player.name} tries to scrap a trade-row card, but the row is empty")
            return

        if not hasattr(game, "scrap_heap"):
            game.scrap_heap = []
        scrap_heap = game.scrap_heap

        agent = getattr(player, "agent", None)

        # Agent path
        if agent is not None and hasattr(agent, "choose_index"):
            idx = agent.choose_index(
                "Choose trade-row index to remove (0-based): ",
                options=[(c.get("name","?") if c else "(empty)") for c in game.trade_row],
            )
            if not (isinstance(idx, int) and 0 <= idx < len(game.trade_row)):
                _log(game, "Invalid trade-row choice; nothing removed")
                return
            removed = game.trade_row.pop(idx)
            if removed is not None:
                scrap_heap.append(removed)
            _log(game, f"{player.name} removes {(removed.get('name','?') if removed else '(empty)')} from trade row")
            if hasattr(game, "refill_trade_row"):
                game.refill_trade_row()
            return

        # Human path (supports cancel)
        if getattr(player, "human", False):
            ui_print("Trade Row:", [f"{i+1}:{(c.get('name','?') if c else '(empty)')}" for i, c in enumerate(game.trade_row)])
            pick = ui_input("Choose a trade row index to remove (1-based, or 'x' to cancel): ").strip().lower()
            if pick in ("x", "cancel", ""):
                return
            try:
                idx0 = int(pick) - 1
                if 0 <= idx0 < len(game.trade_row):
                    removed = game.trade_row.pop(idx0)
                    if removed is not None:
                        scrap_heap.append(removed)
                    _log(game, f"{player.name} removes {(removed.get('name','?') if removed else '(empty)')} from trade row")
                    if hasattr(game, "refill_trade_row"):
                        game.refill_trade_row()
                else:
                    ui_print("Invalid index.")
            except ValueError:
                ui_print("Invalid input.")
            return

        # Auto path: pick a filled slot deterministically (tests may monkeypatch random.choice)
        filled = [i for i, c in enumerate(game.trade_row) if c is not None]
        if not filled:
            _log(game, "Trade row is empty; nothing removed")
            return
        idx = random.choice(filled)
        removed = game.trade_row.pop(idx)
        if removed is not None:
            scrap_heap.append(removed)
        _log(game, f"{player.name} removes {removed.get('name','?')} from trade row")
        if hasattr(game, "refill_trade_row"):
            game.refill_trade_row()
        return

    if etype == "copy_target_ship":
        # Copy on-play effects from a ship you played this turn.
        ships_in_play = getattr(player, "in_play", [])
        if not ships_in_play:
            _log(game, f"{player.name} has no ships to copy")
            return

        agent = getattr(player, "agent", None)

        if agent is not None and hasattr(agent, "choose_index"):
            idx = agent.choose_index(
                "Choose a ship to copy (0-based): ",
                options=[c.get('name','?') for c in ships_in_play],
            )
            if not (isinstance(idx, int) and 0 <= idx < len(ships_in_play)):
                _log(game, "Invalid ship choice; nothing copied")
                return
            target_ship = ships_in_play[idx]

        elif getattr(player, "human", False):
            ui_print("Ships in play:", [f"{i+1}:{c.get('name','?')}" for i, c in enumerate(ships_in_play)])
            ans = ui_input("Choose a ship to copy (1-based): ").strip()
            try:
                idx1 = int(ans) - 1
                if not (0 <= idx1 < len(ships_in_play)):
                    raise ValueError
                target_ship = ships_in_play[idx1]
            except ValueError:
                ui_print("Invalid choice.")
                return
        else:
            target_ship = ships_in_play[0]

        extra_effects = _collect_on_play_effects(target_ship)
        if extra_effects:
            _log(game, f"{player.name} copies {target_ship.get('name','?')} → {_fmt_list(extra_effects)}")
            apply_effects(extra_effects, player, opponent, game)
        else:
            _log(game, f"{player.name} copies {target_ship.get('name','?')} (no on-play effects)")
        return

    # Unknown: log for visibility (keeps tests stable even if a new effect sneaks in)
    _log(game, f"(debug) Unhandled effect type: {etype}")
    return