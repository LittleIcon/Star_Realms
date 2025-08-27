# starrealms/runner/human.py
"""
Human player turn loop / runner for Star Realms.

- Renders state each time it changes
- Handles play, buy, attack, info, use, discard view, end turn
- Delegates 'info' to starrealms.ui.resolve_info for robust parsing
"""

from __future__ import annotations
import re

from starrealms.ui import (
    print_state,
    print_new_log,
    describe_card,
    use_action,
    resolve_info,   # robust info UI (supports 'h 1', 'h1', 't 3', 'name Cutter', etc.)
    resolve_attack, # interactive attack (outpost gating, base defense costs)
)
# If other modules are needed by your engine, import them here.


def _parse_int_choice(s: str) -> int | None:
    """
    Parse a 1-based index from user input, tolerating forms like '1', '1)', '1,', '  1  '.
    Returns a 0-based index, or None if not a number.
    """
    if not s:
        return None
    m = re.match(r"\s*(\d+)", s)
    if not m:
        return None
    return int(m.group(1)) - 1


def human_turn(game, last_log_len: int) -> int:
    """
    Run a full human turn loop for the current player in `game`.
    Returns the updated last_log_len for incremental log printing.
    """
    game.start_turn()
    p = game.current_player()
    o = game.opponent()
    needs_redraw = True
    
       # NEW: mark whose UI is human-controlled this turn
    setattr(p, "human", True)
    setattr(o, "human", False)

    while True:
        if needs_redraw:
            print_state(game)
            last_log_len = print_new_log(game, last_log_len)
            needs_redraw = False

        cmd = input(
            "🎮 Action: [pa]=play all, [p]=play one, [b]=buy, [a]=attack, "
            "[i]=info, [u]=use (base/ship), [d]=discards, [e]=end > "
        ).strip().lower()
        state_changed = False

        # --- play all ---
        if cmd == "pa":
            if p.hand:
                # copy to avoid mutating while iterating
                for card in list(p.hand):
                    print(f"🎴 Playing {card['name']}…")
                    p.play_card(card, o, game)
                    # show only the new log lines caused by THIS card
                    last_log_len = print_new_log(game, last_log_len)
                state_changed = True
            else:
                print("🫳 Your hand is empty.")

        # --- play one ---
        elif cmd == "p":
            if not p.hand:
                print("🫳 Your hand is empty.")
            else:
                for i, c in enumerate(p.hand, start=1):
                    print(f"{i}: {c['name']}")
                sel = input("▶️  Play which index (1-based)? > ").strip()
                idx = _parse_int_choice(sel)
                if idx is None:
                    print("↩️  Cancelled.")
                elif 0 <= idx < len(p.hand):
                    card = p.hand[idx]
                    print(f"🎴 Playing {card['name']}…")
                    p.play_card(card, o, game)
                    # Show the new log lines just from this card
                    last_log_len = print_new_log(game, last_log_len)
                    state_changed = True
                else:
                    print("❌ Invalid index.")

        # --- buy ---
        elif cmd == "b":
            # Show current trade (coins) up front
            print(f"🛒 Trade Row (you have 🟡 {p.trade_pool}):")
            print("    ✅ = you can afford   ❌ = not enough trade")

            # List trade row with affordability marks
            for i, c in enumerate(game.trade_row, start=1):
                if c:
                    cost = c.get("cost", 0)
                    mark = " ✅" if p.trade_pool >= cost else " ❌"
                    print(f"  {i}: {c['name']} (cost {cost}){mark}")
                else:
                    print(f"  {i}: —")

            # Explorer as a numbered option, with affordability mark
            explorer_idx = len(game.trade_row) + 1
            explorer_mark = " ✅" if p.trade_pool >= 2 else " ❌"
            print(f"  {explorer_idx}: Explorer (cost 2){explorer_mark}")
            print("  x: Cancel")

            sel = input(f"🛍️  Buy which? (1-{explorer_idx}, or 'x' to cancel) > ").strip().lower()

            if sel == "x":
                print("↩️  Cancelled buy.")
            else:
                idx = _parse_int_choice(sel)
                if idx is None:
                    print("❌ Missing index.")
                elif idx == explorer_idx - 1:  # Explorer is last slot
                    if getattr(p, "trade_pool", 0) >= 2:
                        game.buy_explorer(p)
                        print(f"🛒 Bought Explorer. Remaining 🟡 {p.trade_pool}.")
                        state_changed = True
                    else:
                        print("💸 Not enough trade for Explorer.")
                elif 0 <= idx < len(game.trade_row):
                    card = game.trade_row[idx]
                    if card is None:
                        print("❌ That slot is empty.")
                    elif p.buy_card(card, game):
                        game.log.append(f"{p.name} buys {card['name']}")
                        print(f"🛒 Bought {card['name']}. Remaining 🟡 {p.trade_pool}.")
                        game.refill_trade_row()
                        state_changed = True
                    else:
                        print("💸 Not enough trade.")
                else:
                    print("❌ Invalid index.")

        # --- attack ---
        elif cmd == "a":
            if getattr(p, "combat_pool", 0) > 0:
                # Use interactive attack that enforces outpost-first and base defense costs.
                resolve_attack(p, o, game)
                print("⚔️  Attack resolved.")
                state_changed = True
            else:
                print("🪫 No combat available.")

        # --- info ---
        elif cmd == "i":
            # Delegate to the robust info UI (keeps all parsing in one place)
            resolve_info(game)
            state_changed = False  # viewing info doesn't change state

        # --- use (bases & ships) ---
        elif cmd == "u":
            print("\n🧭 Use (base/ship)")
            use_action(p, o, game)
            last_log_len = print_new_log(game, last_log_len)
            state_changed = True

        # --- discard view ---
        elif cmd == "d":
            def _idx_names(cards):
                return ", ".join(f"{i}:{c['name']}" for i, c in enumerate(cards, start=1)) or "(empty)"
            print("\n🗂️  Discards")
            print(f"  {p.name}: [{_idx_names(getattr(p, 'discard_pile', []))}]")
            print(f"  {o.name}: [{_idx_names(getattr(o, 'discard_pile', []))}]\n")

        # --- end turn ---
        elif cmd == "e":
            game.end_turn()
            last_log_len = print_new_log(game, last_log_len)
            break

        else:
            print("🤷 Invalid command.")

        # Always print any new log entries after an action
        last_log_len = print_new_log(game, last_log_len)
        if state_changed:
            needs_redraw = True

    return last_log_len