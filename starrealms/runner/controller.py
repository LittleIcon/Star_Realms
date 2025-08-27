# starrealms/runner/controller.py

from typing import Optional, Union
from starrealms.ui import print_state, print_new_log, resolve_attack
from starrealms.effects import apply_effects  # reserved for other effect handling


def _list_bases_for_choice(bases):
    items = []
    for i, b in enumerate(bases, start=1):
        tag = " [Outpost]" if b.get("outpost") else ""
        items.append(f"{i}:{b['name']} (def {b.get('defense', '?')}){tag}")
    return ", ".join(items) if items else "(none)"


def _spend_to_destroy_base(attacker, defender, base, game) -> bool:
    """Spend attacker's combat equal to base defense and scrap the base. Return True if destroyed."""
    defense = int(base.get("defense", 0) or 0)
    if attacker.combat_pool < defense:
        return False
    attacker.combat_pool -= defense
    # move base to scrap and remove from play
    try:
        defender.bases.remove(base)
    except ValueError:
        pass
    if hasattr(game, "scrap_heap"):
        game.scrap_heap.append(base)
    game.log.append(f"{attacker.name} destroys {defender.name}'s {base['name']} by combat")
    return True


def _ai_resolve_attack(p, o, game) -> None:
    """
    Non-interactive attack resolution for AI:
      1) While outposts exist and affordable, destroy the cheapest outpost.
      2) Otherwise, dump remaining combat into authority.
    Optional: you can expand to destroy cheap normal bases before face damage.
    """
    # Step 1: clear outposts as long as we can afford one
    while True:
        outposts = [b for b in o.bases if b.get("outpost")]
        if not outposts:
            break
        outposts.sort(key=lambda b: int(b.get("defense", 0) or 0))
        destroyed = False
        for b in outposts:
            if p.combat_pool >= int(b.get("defense", 0) or 0):
                _spend_to_destroy_base(p, o, b, game)
                destroyed = True
                break
        if not destroyed:
            # can't afford any outpost; stop the attack step here
            return

    # Step 2: (optional) destroy a cheap normal base if it's very cheap; else face
    normals = [b for b in o.bases if not b.get("outpost")]
    if normals:
        normals.sort(key=lambda b: int(b.get("defense", 0) or 0))
        # very simple heuristic: only destroy if its defense <= half our pool
        if (
            p.combat_pool > 0
            and p.combat_pool >= int(normals[0].get("defense", 0) or 0)
            and int(normals[0].get("defense", 0) or 0) <= max(1, p.combat_pool // 2)
        ):
            _spend_to_destroy_base(p, o, normals[0], game)

    # Step 3: send remaining combat to authority
    if p.combat_pool > 0:
        o.authority -= p.combat_pool
        game.log.append(f"{p.name} deals {p.combat_pool} damage to {o.name}")
        p.combat_pool = 0


def apply_command(
    game,
    cmd: str,
    arg: Optional[Union[int, str]],
    last_log_len: int,
    echo: bool = True,
) -> int:
    """
    Shared executor for both human and AI turns.
    Prints new logs and (for humans) board state after each command.
    """
    p = game.current_player()
    o = game.opponent()

    # -------- play all --------
    if cmd == "pa":
        if echo:
            print("🚀 Played all cards.")
        for card in list(p.hand):
            p.play_card(card, o, game)
        last_log_len = print_new_log(game, last_log_len)
        print_state(game)
        return last_log_len

    # -------- play single (1-based index) --------
    if cmd == "p":
        if isinstance(arg, int):
            if 1 <= arg <= len(p.hand):
                card = p.hand[arg - 1]
                p.play_card(card, o, game)
                if echo:
                    print(f"🎴 Played {card['name']}.")
            else:
                if echo:
                    print("❌ Invalid hand index.")
        else:
            if echo:
                print("↩️  Cancelled.")
        last_log_len = print_new_log(game, last_log_len)
        print_state(game)
        return last_log_len

    # -------- buy (trade row or Explorer) --------
    if cmd == "b":
        if arg == "x":
            if p.trade_pool >= 2:
                game.buy_explorer(p)
                if echo:
                    print("🛒 Bought Explorer.")
            else:
                if echo:
                    print("💸 Not enough trade for Explorer.")
        elif isinstance(arg, int):
            idx0 = arg - 1
            if 0 <= idx0 < len(game.trade_row):
                card = game.trade_row[idx0]
                if card is None:
                    if echo:
                        print("❌ That slot is empty.")
                else:
                    if p.buy_card(card, game):
                        game.log.append(f"{p.name} buys {card['name']}")
                        if echo:
                            print(f"🛒 Bought {card['name']}.")
                        # keep fixed 5-slot behavior
                        game.refill_trade_row()
                    else:
                        if echo:
                            print("💸 Not enough trade.")
            else:
                if echo:
                    print("❌ Invalid index.")
        else:
            if echo:
                print("↩️  Cancelled.")

        last_log_len = print_new_log(game, last_log_len)
        print_state(game)
        return last_log_len

    # -------- attack (human => interactive; AI => auto) --------
    if cmd == "a":
        if echo:
            print(f"⚔️  {p.name} declares an attack.")
        if p.combat_pool <= 0:
            if echo:
                print("🪫 No combat available.")
        else:
            if getattr(p, "human", False):
                # HUMAN: interactive target selection with outpost rules
                resolve_attack(p, o, game)
            else:
                # AI: non-interactive resolution (no prompts)
                _ai_resolve_attack(p, o, game)

        last_log_len = print_new_log(game, last_log_len)
        print_state(game)
        return last_log_len

    # -------- info (human only) --------
    if cmd == "i":
        if getattr(p, "human", False):
            # We import here to avoid circular import at module load.
            try:
                from starrealms.ui import resolve_info, info_from_arg  # type: ignore
            except Exception:
                resolve_info = None
                info_from_arg = None

            # If caller passed inline args (e.g., "h 1", "name Trade"), handle non-interactively.
            if isinstance(arg, str) and arg.strip() and info_from_arg:
                info_from_arg(game, arg.strip())
            elif resolve_info:
                # Fallback to interactive prompt.
                resolve_info(game)
            else:
                print("ℹ️  Info handler not found. Add resolve_info()/info_from_arg() to starrealms/ui.py")
        else:
            if echo:
                print("ℹ️  Info ignored for AI.")
        last_log_len = print_new_log(game, last_log_len)
        return last_log_len

    # -------- use (handled by human UI flow) --------
    if cmd == "u":
        if echo:
            print("(use base/ship is interactive; ignored here)")
        return last_log_len

    # -------- discards quick view --------
    if cmd == "d":
        def _idx_names(cards):
            return ", ".join(f"{i}:{c['name']}" for i, c in enumerate(cards, start=1)) or "(empty)"
        print("\n🗂️  Discards")
        print(f"  {p.name}: [{_idx_names(p.discard_pile)}]")
        print(f"  {o.name}: [{_idx_names(o.discard_pile)}]\n")
        return last_log_len

    # -------- end turn --------
    if cmd == "e":
        if echo:
            print(f"⏭️  {p.name} ends their turn.")
        game.end_turn()
        last_log_len = print_new_log(game, last_log_len)
        return last_log_len

    # -------- fallback --------
    if echo:
        print("🤷 Invalid command.")
    return last_log_len