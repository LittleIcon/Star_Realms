"""
Effect engine for Star Realms.
- Accepts either a single effect dict OR a list of effect dicts.
- Robustly handles 'choose' where each option may be a dict or a list of dicts.
- Now logs all opponent (and player) actions to game.log so turns are fully visible.
"""

import random

def _log(game, msg):
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
        # e.g. amount=2 -> "discard up to 2, then draw that many"
        return f"discard up to {a}, then draw that many"
    return t or str(e)

def _fmt_list(effs):
    parts = []
    for e in (effs if isinstance(effs, list) else [effs]):
        parts.append(_fmt_eff(e))
    return ", ".join(parts)

def _human_pick_index(prompt, max_len):
    while True:
        raw = input(prompt).strip().lower()
        if raw in ("x", "skip", ""):
            return None
        try:
            i = int(raw)
            if 0 <= i < max_len:
                return i
        except ValueError:
            pass
        print("Invalid choice. Enter an index number, or 'x' to cancel.")

def _list_with_idx(cards):
    return ", ".join(f"{i+1}:{c['name']}" for i, c in enumerate(cards)) or "(empty)"

def _prompt_scrap_one_from_pile(pile_label: str, pile, player, game) -> bool:
    """
    Ask the user to pick a single card (1-based) from `pile`.
    Returns True if a card was scrapped, False otherwise.
    """
    if not pile:
        print(f"🪫 Your {pile_label} is empty.")
        return False

    while True:
        print(f"{pile_label.capitalize():<7}: [{_list_with_idx(pile)}]")
        ans = input(f"Pick a {pile_label[:-1]} to scrap (1-based), or 'x' to cancel: ").strip().lower()
        if ans in ("x", ""):
            print("↩️  Cancelled.")
            return False
        if ans.isdigit():
            idx = int(ans) - 1
            if 0 <= idx < len(pile):
                card = pile.pop(idx)
                if hasattr(game, "scrap_heap"):
                    game.scrap_heap.append(card)
                else:
                    player.scrap_heap.append(card)
                game.log.append(f"{player.name} scraps {card['name']} from {pile_label}")
                print(f"🗑️  Scrapped {card['name']}.")
                return True
        print("❗ Invalid index, try again.")

def _force_opponent_discards(game, opponent, n: int) -> None:
    """
    Make the opponent discard n cards. If they have no chooser UI/AI,
    discard from the front (deterministic). Logs each discard.
    """
    n = int(n or 0)
    for _ in range(n):
        if not getattr(opponent, "hand", None):
            _log(game, f"{opponent.name} has no cards to discard")
            return
        # Prefer opponent's own decision method if it exists
        if hasattr(opponent, "choose_discard_index"):
            idx = opponent.choose_discard_index(game, 1)
            if idx is None or not (0 <= idx < len(opponent.hand)):
                idx = 0
        else:
            idx = 0
        card = opponent.hand.pop(idx)
        opponent.discard_pile.append(card)
        _log(game, f"{opponent.name} discards {card['name']} (forced)")
        
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
    amt = effect.get("amount")

    # -------------- branching / containers --------------
    if etype == "choose":
        options = effect.get("options", [])
        if not options:
            return

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

    # -------------- hand / discard manipulation --------------
    if etype in ("discard", "opponent_discards"):
        n = int(amt or 1)
        for _ in range(n):
            if not opponent.hand:
                _log(game, f"{opponent.name} has no cards to discard")
                break

            if getattr(opponent, "human", False):
                # Human opponent MUST discard; no skipping.
                while True:
                    print(f"{opponent.name}, choose a card to discard:")
                    for i, c in enumerate(opponent.hand, start=1):
                        print(f"  {i}: {c['name']}")
                    ans = input("Index (1-based): ").strip()
                    if ans.isdigit():
                        idx = int(ans) - 1
                        if 0 <= idx < len(opponent.hand):
                            card = opponent.hand.pop(idx)
                            opponent.discard_pile.append(card)
                            _log(game, f"{opponent.name} discards {card['name']}")
                            break
                    print("❗ Invalid choice, try again.")
            else:
                # Simple AI strategy: discard the first card
                card = opponent.hand.pop(0)
                opponent.discard_pile.append(card)
                _log(game, f"{opponent.name} discards {card['name']}")
        return
    
    # -------------- scrap from hand or discard (Explorer, Trade Bot, etc.) --------------
    if etype == "scrap_hand_or_discard":
        if not hasattr(player, "scrap_heap"):
            player.scrap_heap = []

        if not player.hand and not player.discard_pile:
            _log(game, f"{player.name} has nothing to scrap")
            return

        if getattr(player, "human", False):
            # robust loop until valid choice or explicit cancel
            while True:
                h_ct, d_ct = len(player.hand), len(player.discard_pile)
                print(f"Hand   : [{_list_with_idx(player.hand)}]")
                print(f"Discard: [{_list_with_idx(player.discard_pile)}]")
                ans = input("Scrap from [h]and or [d]iscard? (x=skip) ").strip().lower()

                if ans in ("x", "skip", ""):
                    print("↩️  Skipped scrapping.")
                    return

                if ans in ("h", "hand"):
                    if h_ct == 0:
                        print("🪫 Your hand is empty. Choose discard or press x to skip.")
                        continue
                    if _prompt_scrap_one_from_pile("hand", player.hand, player, game):
                        return

                elif ans in ("d", "discard"):
                    if d_ct == 0:
                        print("🪫 Your discard is empty. Choose hand or press x to skip.")
                        continue
                    if _prompt_scrap_one_from_pile("discard", player.discard_pile, player, game):
                        return

                else:
                    print("❗ Invalid choice. Type 'h', 'd', or 'x'.")
        else:
            # --- AI / auto ---
            if player.discard_pile:
                card = player.discard_pile.pop(0)
                player.scrap_heap.append(card)
                _log(game, f"{player.name} scraps {card['name']} from discard")
            elif player.hand:
                card = player.hand.pop(0)
                player.scrap_heap.append(card)
                _log(game, f"{player.name} scraps {card['name']} from hand")
        return
            
        # -------------- variable discard then draw --------------
    if etype in ("discard_then_draw", "discard_up_to_then_draw"):
        max_discards = int(amt or 0)
        if max_discards <= 0:
            return

        actual_discards = 0

        if getattr(player, "human", False):
            # Let the human discard 0..N; stop with 'x' / empty
            while actual_discards < max_discards and player.hand:
                print(f"Your hand: [{_list_with_idx(player.hand)}]")
                ans = input(
                    f"Discard a card? ({actual_discards}/{max_discards} so far). "
                    f"Type a 1-based index, or 'x' to stop: "
                ).strip().lower()

                if ans in ("x", "stop", ""):
                    break

                if ans.isdigit():
                    idx = int(ans) - 1
                    if 0 <= idx < len(player.hand):
                        card = player.hand.pop(idx)
                        player.discard_pile.append(card)
                        _log(game, f"{player.name} discards {card['name']} (self)")
                        actual_discards += 1
                    else:
                        print("❗ Invalid index.")
                else:
                    print("❗ Enter a card index or 'x' to stop.")
        else:
            # --- Simple AI: discard as many as allowed (tune later if you want) ---
            while actual_discards < max_discards and player.hand:
                card = player.hand.pop(0)
                player.discard_pile.append(card)
                _log(game, f"{player.name} discards {card['name']} (self, auto)")
                actual_discards += 1

        # Draw the same number you discarded
        for _ in range(actual_discards):
            player.draw_card()

        if actual_discards:
            _log(game, f"{player.name} draws {actual_discards} card(s) after discarding")
        else:
            _log(game, f"{player.name} chose not to discard")
        return

    if etype == "scrap_multiple":
        if not hasattr(player, "scrap_heap"):
            player.scrap_heap = []

        n = int(amt or 0)
        if n <= 0:
            return
        if not player.hand and not player.discard_pile:
            return

        if getattr(player, "human", False):
            print(f"🧹 Scrap {n} {'card' if n==1 else 'cards'} from your hand/discard. (x=finish early)")
            scrapped = 0
            while scrapped < n and (player.hand or player.discard_pile):
                print(f"Hand   : [{_list_with_idx(player.hand)}]")
                print(f"Discard: [{_list_with_idx(player.discard_pile)}]")
                ans = input("Choose pile [h/d] (or 'x' to stop scrapping): ").strip().lower()
                if ans in ("x", ""):
                    break
                if ans not in ("h", "d", "hand", "discard"):
                    print("❗ Invalid choice. Type 'h', 'd', or 'x'.")
                    continue

                if ans.startswith("h"):
                    if not player.hand:
                        print("🪫 Your hand is empty.")
                        continue
                    if _prompt_scrap_one_from_pile("hand", player.hand, player, game):
                        scrapped += 1
                else:
                    if not player.discard_pile:
                        print("🪫 Your discard is empty.")
                        continue
                    if _prompt_scrap_one_from_pile("discard", player.discard_pile, player, game):
                        scrapped += 1

            if scrapped:
                _log(game, f"{player.name} scrapped {scrapped} card(s)")
            return

        # --- AI ---
        scrapped = 0
        for _ in range(n):
            if player.discard_pile:
                card = player.discard_pile.pop(0)
                player.scrap_heap.append(card)
                _log(game, f"{player.name} scraps {card['name']} from discard")
                scrapped += 1
            elif player.hand:
                card = player.hand.pop(0)
                player.scrap_heap.append(card)
                _log(game, f"{player.name} scraps {card['name']} from hand")
                scrapped += 1
            else:
                break
        if scrapped:
            _log(game, f"{player.name} scrapped {scrapped} card(s)")
        return

    # -------------- board / market interaction --------------
    if etype == "destroy_base":
        outposts = [b for b in opponent.bases if b.get("outpost")]
        pool = outposts if outposts else opponent.bases
        if not pool:
            _log(game, f"{player.name} tries to destroy a base, but none available")
            return

        if getattr(player, "human", False):
            print("Opponent bases:", [f"{i+1}:{b['name']}{' [Outpost]' if b.get('outpost') else ''}" for i, b in enumerate(opponent.bases)])
            try:
                idx = int(input("Choose base index to destroy (1-based): ").strip()) - 1
                base = opponent.bases[idx]
                if outposts and not base.get("outpost"):
                    print("You must destroy an outpost first.")
                    return
                opponent.bases.pop(idx)
                print(f"Destroyed {base['name']}.")
                _log(game, f"{player.name} destroys {opponent.name}'s {base['name']}")
            except (ValueError, IndexError):
                print("Invalid choice.")
        else:
            if outposts:
                for i, b in enumerate(opponent.bases):
                    if b.get("outpost"):
                        destroyed = opponent.bases.pop(i)
                        _log(game, f"{player.name} destroys {opponent.name}'s {destroyed['name']}")
                        break
            else:
                destroyed = opponent.bases.pop(0)
                _log(game, f"{player.name} destroys {opponent.name}'s {destroyed['name']}")
        return

    if etype in ("destroy_target_trade_row", "scrap_from_trade_row"):
        if not game.trade_row:
            _log(game, f"{player.name} tries to scrap a trade-row card, but the row is empty")
            return

        if getattr(player, "human", False):
            print("Trade Row:", [f"{i+1}:{c['name']}" for i, c in enumerate(game.trade_row)])
            pick = input("Choose a trade row index to remove (1-based, or 'x' to cancel): ").strip().lower()
            if pick in ("x", "cancel", ""):
                return
            try:
                idx0 = int(pick) - 1
                if 0 <= idx0 < len(game.trade_row):
                    removed = game.trade_row.pop(idx0)
                    if hasattr(game, "scrap_heap"):
                        game.scrap_heap.append(removed)
                    game.refill_trade_row()
                    print(f"Removed {removed['name']} from trade row.")
                    _log(game, f"{player.name} scraps {removed['name']} from the trade row")
            except ValueError:
                pass
        else:
            removed = random.choice(game.trade_row)
            game.trade_row.remove(removed)
            if hasattr(game, "scrap_heap"):
                game.scrap_heap.append(removed)
            game.refill_trade_row()
            _log(game, f"{player.name} scraps {removed['name']} from the trade row")
        return

    if etype == "ally_any_faction":
        setattr(player, "ally_wildcard_active", True)
        _log(game, f"{player.name}'s base counts as all factions for ally this turn")
        return

    if etype == "per_ship_combat":
        bonus = int(amt or 0)
        curr = getattr(player, "per_ship_combat_bonus", 0)
        setattr(player, "per_ship_combat_bonus", curr + bonus)
        _log(game, f"{player.name} gains +{bonus} combat per ship for this turn")
        return

    if etype == "topdeck_next_purchase":
        player.topdeck_next_purchase = True
        _log(game, f"{player.name} will top-deck their next purchase")
        return

    if etype == "copy_target_ship":
        source = player.in_play[-1] if player.in_play else None
        depth = getattr(player, "_copy_depth", 0)
        if depth >= 1:
            return

        eligible = [
            c for c in player.in_play
            if c is not source and c.get("type") == "ship"
        ]

        target = None
        if not eligible:
            _log(game, f"{player.name} plays Stealth Needle but has no ship to copy")
            return

        if getattr(player, "human", False):
            print("Choose a ship to copy with Stealth Needle:")
            for i, c in enumerate(eligible):
                print(f"  {i+1}: {c['name']} [{c.get('faction','?')}]")
            while True:
                raw = input("Index (1-based, or 'x' to cancel): ").strip().lower()
                if raw in ("x", "cancel", ""):
                    return
                try:
                    i = int(raw) - 1
                    if 0 <= i < len(eligible):
                        target = eligible[i]
                        break
                except ValueError:
                    pass
                print("Invalid choice.")
        else:
            target = eligible[-1]

        if not target:
            return

        if source is not None:
            source["_copied_from"] = target["name"]

        _log(game, f"{player.name}'s Stealth Needle copies {target['name']}")

        try:
            setattr(player, "_copy_depth", depth + 1)
            apply_effects(target.get("effects", []), player, opponent, game)

            same_faction = any(
                c is not target and c.get("faction") == target.get("faction")
                for c in player.in_play
            )
            if same_faction or getattr(player, "ally_wildcard_active", False):
                apply_effects(target.get("ally", []), player, opponent, game)
        finally:
            setattr(player, "_copy_depth", depth)
        return