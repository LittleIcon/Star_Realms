# starrealms/ui.py
"""
Presentation & user-interaction helpers for Star Realms.
Keeps all printing, formatting, and prompts out of game logic.


def _abilities(card):
    return list(card.get("abilities", []) or [])

def _has_scrap(card):
    # NEW schema
    if any(ab.get("trigger") == "scrap_activated" for ab in _abilities(card)):
        return True
    # Legacy
    return bool(card.get("scrap"))

This module provides:
- print_state(game): pretty board renderer
- print_new_log(game, last_len): incremental log printing
- resolve_info(game): interactive info prompt
- info_from_arg(game, s): non-interactive info query (e.g., "h 1", "name Trade")
- resolve_attack(p, o, g): human attack targeting with outpost rules
- use_action(p, o, g): activate bases / scrap ships UI
"""
from starrealms.view.ui_common import ui_input, ui_print, ui_log


from typing import List, Dict, Optional

# =========================
# Basic card access helpers
# =========================


def _card_name(c: Dict) -> str:
    return c.get("name", "?")


def _card_cost(c: Dict):
    return c.get("cost", "?")


def _card_def(c: Dict) -> int:
    return int(c.get("defense", 0) or 0)


def _is_outpost(c: Dict) -> bool:
    return bool(c.get("outpost"))


def _faction_abbrev(f: Optional[str]) -> str:
    """Compact faction tag for row labels."""
    if not f:
        return ""
    return {
        "Star Empire": "SE",
        "Trade Federation": "TF",
        "Machine Cult": "MC",
        "Blob": "Blob",
        "Neutral": "N",
    }.get(f, f)


def _trade_row_entry(idx: int, c: Optional[Dict]) -> str:
    """Always show 'index:...' with safe formatting."""
    if not c:
        return f"{idx}:—"
    name = _card_name(c)
    cost = _card_cost(c)
    fac = _faction_abbrev(c.get("faction"))
    if fac:
        return f"{idx}:{name} ({fac}, {cost})"
    return f"{idx}:{name}({cost})"


# =========================
# Compact list / detail UI
# =========================


def _list_zone(zone_cards: List[Dict], title: str) -> None:
    """List zone with 1-based indices"""
    if not zone_cards:
        print(f"{title}: [∅]")
        return
    print(f"{title}:")
    for i, c in enumerate(zone_cards, 1):
        # Use a compact uniform label
        fac = _faction_abbrev(c.get("faction"))
        cost = _card_cost(c)
        if fac:
            print(f"  {i}:{_card_name(c)} ({fac}, {cost})")
        else:
            print(f"  {i}:{_card_name(c)}({cost})")


def _print_inline_card(card: Dict) -> None:
    """Compact one-screen summary for info lists."""
    name = _card_name(card)
    faction = card.get("faction", "Neutral")
    ctype = card.get("type", "card")
    cost = _card_cost(card)
    defense = card.get("defense")
    outpost = _is_outpost(card)

    print(f"**{name}**  ({faction} • {ctype} • cost {cost})")
    if defense:
        print(f"🛡️ Defense: {defense}" + (" (Outpost)" if outpost else ""))

    def _fmt_effects_any(effs, label: str) -> None:
        if not effs:
            return
        if isinstance(effs, dict):
            effs = [effs]
        parts = []
        for e in effs:
            if not isinstance(e, dict):
                parts.append(str(e))
                continue
            t = e.get("type", "?")
            if t in ("choose", "choice"):
                opts = e.get("options", [])
                parts.append(f"choose one of {len(opts)} options")
                continue
            amt = e.get("amount")
            trig = e.get("trigger")
            piece = t + (f"+{amt}" if amt not in (None, "") else "")
            if trig:
                piece += f" on {trig}"
            parts.append(piece)
        if parts:
            print(f"{label}: " + ", ".join(parts))

    _fmt_effects_any(card.get("effects"), "Effects")
    _fmt_effects_any(card.get("on_play"), "On Play")
    _fmt_effects_any(card.get("activated"), "Activated")
    _fmt_effects_any(card.get("ally"), "Ally")
    _fmt_effects_any(card.get("passive"), "Passive")
    _fmt_effects_any(card.get("scrap"), "Scrap")


# =========================
# Pretty printing helpers
# =========================


def fmt_effect(e: Dict) -> str:
    t = e.get("type")
    amt = e.get("amount")
    if t == "trade":
        return f"trade +{amt}"
    if t == "combat":
        return f"combat +{amt}"
    if t == "draw":
        return f"draw {amt}"
    if t == "authority":
        return f"authority +{amt}"
    if t in ("discard", "opponent_discards"):
        return f"opponent discards {amt}"
    if t == "scrap_hand_or_discard":
        return "scrap a card from your hand or discard"
    if t == "scrap_multiple":
        return f"scrap {amt} cards from hand/discard"
    if t == "destroy_base":
        return "destroy target base"
    if t == "destroy_target_trade_row":
        return "scrap a card from the trade row"
    if t == "ally_any_faction":
        return "this base counts as all factions for ally"
    if t == "per_ship_combat":
        return f"+{amt} combat per ship this turn"
    if t == "topdeck_next_purchase":
        return "top-deck your next purchase"
    if t == "copy_target_ship":
        return "copy another ship you played this turn"
    if t == "start_of_turn":
        inner = e.get("effect")
        return f"at start of turn: {fmt_effect(inner) if isinstance(inner, dict) else inner}"
    if t == "choose":
        return "choose one option"
    return str(e)


def fmt_effect_block(title: str, effects) -> str:
    """Pretty multiline block for describe_card"""
    if not effects:
        return ""
    if isinstance(effects, dict):
        effects = [effects]
    lines = [f"{title}:"]
    for eff in effects:
        if isinstance(eff, dict) and eff.get("type") == "choose":
            lines.append("  choose one:")
            for i, opt in enumerate(eff.get("options", []), 1):
                pretty = ", ".join(
                    fmt_effect(x) for x in (opt if isinstance(opt, list) else [opt])
                )
                lines.append(f"    • Option {i}: {pretty}")
        else:
            lines.append(f"  • {fmt_effect(eff)}")
    return "\n".join(lines)


def describe_card(c: Dict) -> str:
    """Detailed multi-line description"""
    header = f"{c['name']} ({c['faction']}, {c['type']}, cost {c['cost']})"
    if c["type"] in ("base", "outpost"):
        header += f" | defense {c.get('defense','?')}"
        if c.get("outpost"):
            header += " | OUTPOST"

    parts = [header]
    if c.get("name") == "Stealth Needle" and "_copied_from" in c:
        parts.append(f"(Copied this turn from: {c['_copied_from']})")

    parts.append(fmt_effect_block("On Play", c.get("on_play", [])))
    parts.append(fmt_effect_block("Activated", c.get("activated", [])))
    parts.append(fmt_effect_block("Ally", c.get("ally", [])))
    parts.append(fmt_effect_block("Passive", c.get("passive", [])))
    parts.append(fmt_effect_block("Scrap", c.get("scrap", [])))
    parts.append(fmt_effect_block("Effects", c.get("effects", [])))

    if "choice" in c:
        parts.append(
            fmt_effect_block(
                "Choice",
                [{"type": "choose", "options": [c["choice"][0:1], c["choice"][1:2]]}],
            )
        )
    if "conditional" in c:
        cond = c["conditional"]
        req = []
        if "require_bases" in cond:
            req.append(f"{cond['require_bases']}+ bases")
        parts.append("Conditional: " + (" and ".join(req) if req else "see card"))
        cond_effects = cond.get("effects") or (
            [cond["effect"]] if cond.get("effect") else []
        )
        parts.append(fmt_effect_block("Conditional effects", cond_effects))
    return "\n".join(p for p in parts if p)


# =========================
# Indexed label helpers
# =========================


def _idx_names(cards: List[Dict]) -> str:
    return ", ".join(f"{i}:{c['name']}" for i, c in enumerate(cards, start=1)) or "∅"


def _idx_names_inplay(cards: List[Dict]) -> str:
    def _nm(c):
        if c.get("name") == "Stealth Needle" and "_copied_from" in c:
            return f"{c['name']}→{c['_copied_from']}"
        return c["name"]

    return ", ".join(f"{i}:{_nm(c)}" for i, c in enumerate(cards, start=1)) or "∅"


def _idx_names_bases(cards: List[Dict]) -> str:
    """
    Include defense and mark outposts. Example:
      1:Defense Center[4]⛨, 2:Space Station[4]
    """
    if not cards:
        return "∅"
    parts = []
    for i, b in enumerate(cards, start=1):
        tag = "⛨" if b.get("outpost") else ""
        defn = b.get("defense", "?")
        parts.append(f"{i}:{b['name']}[{defn}]{tag}")
    return ", ".join(parts)


# =========================
# State renderer & log
# =========================


def print_state(game) -> None:
    """
    Pretty print the current public state for the current player (p) and opponent (o).
    Expects game to provide: turn_number, trade_row, current_player(), opponent()
    """
    p = game.current_player()
    o = game.opponent()

    row_items = []
    for i, c in enumerate(game.trade_row, start=1):
        row_items.append(_trade_row_entry(i, c))
    trade_row_str = ", ".join(row_items) if row_items else "∅"

    def _deck_len(pl):
        return len(getattr(pl, "deck", []))

    def _discard_len(pl):
        return len(getattr(pl, "discard_pile", []))

    def _hand_len(pl):
        return len(getattr(pl, "hand", []))

    print("\n==============================")
    print(f"🕒 TURN {game.turn_number}: {p.name}")
    print("------------------------------")
    print(f"👤 {p.name}: 💚 {p.authority}  |  🟡 {p.trade_pool}  |  🔺 {p.combat_pool}")
    print(
        f"📦 Deck: {_deck_len(p)}  |  🗑️ Discard: {_discard_len(p)}  |  🃏 Hand: {_hand_len(p)}"
    )
    print(f"✋ Hand: [{_idx_names(p.hand)}]")
    print(f"🚀 In Play: [{_idx_names_inplay(p.in_play)}]")
    print(f"🏰 Bases: [{_idx_names_bases(p.bases)}]")
    print("")
    print(f"👤 {o.name}: 💚 {o.authority}")
    print(
        f"📦 Deck: {_deck_len(o)}  |  🗑️ Discard: {_discard_len(o)}  |  🃏 Hand: {_hand_len(o)}"
    )
    print(f"🚀 {o.name} In Play: [{_idx_names_inplay(o.in_play)}]")
    print(f"🏰 {o.name} Bases: [{_idx_names_bases(o.bases)}]")
    print("")
    print(f"🛒 Trade Row: [{trade_row_str}]  |  ✨ Explorer(2)")
    print("==============================")


def print_new_log(game, last_len: int) -> int:
    """Print only new log entries and return the new length."""
    if not hasattr(game, "log"):
        return last_len
    new_entries = game.log[last_len:]
    for line in new_entries:
        print(f"• {line}")
    return len(game.log)


# =========================
# Info (interactive & inline)
# =========================


def _zone_cards(game, who: Optional[str], zone_key: str) -> Optional[List[Dict]]:
    """
    who: not used (kept for compatibility if you ever extend)
    zone_key: h,t,b,ip,d or opponent variants ob,oip,od
    """
    p = game.current_player()
    o = game.opponent()

    if zone_key == "h":
        return getattr(p, "hand", [])
    if zone_key == "t":
        return list(getattr(game, "trade_row", []))
    if zone_key == "b":
        return getattr(p, "bases", [])
    if zone_key == "ip":
        return getattr(p, "in_play", [])
    if zone_key == "d":
        return getattr(p, "discard_pile", [])

    if zone_key == "ob":
        return getattr(o, "bases", [])
    if zone_key == "oip":
        return getattr(o, "in_play", [])
    if zone_key == "od":
        return getattr(o, "discard_pile", [])

    return None


def _search_all_zones_for_name(game, query: str) -> bool:
    """Search all visible zones and print detailed card info if matches found. Returns True if anything matched."""
    p = game.current_player()
    o = game.opponent()
    found = False

    def _search(where: str, cards: List[Dict]):
        nonlocal found
        for c in cards:
            if query.lower() in _card_name(c).lower():
                print(f"— {where} —")
                print(describe_card(c), end="\n\n")
                found = True

    _search("Hand", getattr(p, "hand", []))
    _search("In Play", getattr(p, "in_play", []))
    _search("Bases", getattr(p, "bases", []))
    _search("Discard", getattr(p, "discard_pile", []))
    _search("Trade Row", [c for c in getattr(game, "trade_row", []) if c])
    _search("Opp In Play", getattr(o, "in_play", []))
    _search("Opp Bases", getattr(o, "bases", []))
    _search("Opp Discard", getattr(o, "discard_pile", []))
    return found


def info_from_arg(game, s: str) -> None:
    """
    Non-interactive info: parse 'h', 'h 1', 't 3', or ANY card name.
    - Lists stay compact (then prompt inline for a number/name or 'x' to go back)
    - Single-card lookups show full details via describe_card
    """
    s = (s or "").strip()
    if not s:
        print("Usage: i <zone> [index]  or  i <card name>")
        print("Zones: h, t, b, ip, d, ob, oip, od")
        return

    tokens = s.split()
    head = tokens[0].lower()
    known_zones = {"h", "t", "b", "ip", "d", "ob", "oip", "od"}

    # If user typed a zone…
    if head in known_zones:
        idx = None
        if len(tokens) >= 2 and tokens[1].isdigit():
            idx = int(tokens[1])

        cards = _zone_cards(game, "p", head)
        if cards is None:
            print("Unknown zone. Use: h, t, b, ip, d, ob, oip, od  or a card name")
            return

        title_map = {
            "h": "✋ Hand",
            "t": "🛒 Trade Row",
            "b": "🏰 Bases",
            "ip": "🚀 In Play",
            "d": "🗑️ Discard",
            "ob": "🏰 Opp Bases",
            "oip": "🚀 Opp In Play",
            "od": "🗑️ Opp Discard",
        }

        # No index -> compact list, then a quick selector for number/name/'x'
        if idx is None:
            _list_zone(cards, title_map.get(head, "Zone"))
            # NEW: inline prompt for detail
            raw = ui_input(
                "Detail which? Enter number, card name, or 'x' to go back: "
            ).strip()
            if not raw or raw.lower() in ("x", "back"):
                return
            if raw.isdigit():
                i = int(raw)
                if 1 <= i <= len(cards):
                    print(describe_card(cards[i - 1]))
                    print()
                else:
                    print(f"Index out of range for that zone (1..{len(cards)}).")
                return
            # Otherwise treat as name search (within all zones, more useful)
            if not _search_all_zones_for_name(game, raw):
                print(f"No cards matching '{raw}'.")
            return

        # If index was provided directly
        if idx < 1 or idx > len(cards):
            print(f"Index out of range for that zone (1..{len(cards)}).")
            return
        print(describe_card(cards[idx - 1]))
        print()
        return

    # If it's not a zone keyword, treat the entire input as a name query (NEW).
    query = s
    if not _search_all_zones_for_name(game, query):
        print(f"No cards matching '{query}'.")
    return


def resolve_info(game) -> None:
    """
    Interactive info prompt. Now supports:
      i h            -> lists hand, then lets you enter a number, a name, or 'x'
      i t 3          -> detail for trade_row[3]
      i <any name>   -> search by name across zones
    """
    print("ℹ️  Info target: (h/t/b/ob/ip/oip/d/od [index]) or any card name: ", end="")
    s = ui_input().strip()
    info_from_arg(game, s)


# =========================
# Attack resolution (human)
# =========================


def resolve_attack(p, o, g) -> None:
    """
    Spend the active player's combat pool against legal targets, enforcing
    Outpost blocking rules:

      - If the defender has any Outposts, you may only target Outposts.
      - Once no Outposts remain, you may target any Base or Authority.
      - Destroying a base costs combat equal to its defense, all-or-nothing.
      - You may make multiple selections until combat is 0 or you choose Done.

    This is purely UI; it mutates state and logs actions.
    """
    if p.combat_pool <= 0:
        print("🪫 No combat available.")
        return

    while p.combat_pool > 0:
        outposts = [b for b in o.bases if b.get("outpost")]
        must_hit_outpost = bool(outposts)

        print(f"\n⚔️  Combat pool: {p.combat_pool}")
        if o.bases:
            print(f"🏰 Enemy Bases: [{_idx_names_bases(o.bases)}]")
        else:
            print("🏰 Enemy Bases: ∅")

        # Build target list
        targets = []
        labels = []

        # If any outposts: only outposts are legal
        if must_hit_outpost:
            for b in outposts:
                targets.append(("base", b))
                labels.append(f"Destroy {b['name']} (def {b.get('defense','?')})")
        else:
            # all bases are legal
            for b in o.bases:
                targets.append(("base", b))
                labels.append(f"Destroy {b['name']} (def {b.get('defense','?')})")
            # and authority
            targets.append(("face", None))
            labels.append(f"Hit authority (deal up to {p.combat_pool})")

        # Show menu
        print("Targets:")
        for i, lbl in enumerate(labels, start=1):
            print(f"  {i}: {lbl}")
        print("  x: Done (end attack)")

        raw = ui_input("Pick target (1-based), or 'x': ").strip().lower()
        if raw in ("x", "done", ""):
            break

        try:
            ti = int(raw) - 1
            if ti < 0 or ti >= len(targets):
                print("Invalid choice.")
                continue
        except ValueError:
            print("Invalid choice.")
            continue

        kind, payload = targets[ti]

        if kind == "face":
            # Let the player choose how much damage to spend (don’t auto-dump all)
            while True:
                print(f"You have {p.combat_pool} combat.")
                amt_raw = (
                    ui_input(
                        f"How much to deal to {o.name}? (1..{p.combat_pool}, or 'x' to cancel) "
                    )
                    .strip()
                    .lower()
                )
                if amt_raw in ("x", "", "cancel"):
                    # back to target selection without spending
                    break
                try:
                    spend = int(amt_raw)
                    if 1 <= spend <= p.combat_pool:
                        p.combat_pool -= spend
                        o.authority -= spend
                        g.log.append(f"{p.name} deals {spend} damage to {o.name}")
                        print(
                            f"💥 {o.name} takes {spend} damage. ({o.authority} authority left)"
                        )
                        # don’t break out of the whole attack loop; let them choose again
                        break
                except ValueError:
                    pass
                print("Invalid amount. Enter a number within range, or 'x' to cancel.")
            continue  # back to the target menu

        if kind == "base":
            base = payload
            need = int(base.get("defense", 0) or 0)
            if p.combat_pool < need:
                print(f"Not enough combat to destroy {base['name']} (need {need}).")
                continue
            # Pay and destroy
            p.combat_pool -= need
            try:
                o.bases.remove(base)
            except ValueError:
                pass
            if hasattr(g, "scrap_heap"):
                g.scrap_heap.append(base)
            g.log.append(
                f"{p.name} destroys {o.name}'s {base['name']} (spent {need} combat)"
            )
            print(f"🏚️  Destroyed {base['name']}.")
            # continue loop: you can destroy more or hit face next if no outposts left


# =========================
# Use (bases & ships)
# =========================


def use_action(p, o, g) -> None:
    """List scrappable bases/ships (legacy + new schema), confirm, and scrap."""
    scrappable = []
    for c in getattr(p, "in_play", []):
        if c.get("type") == "ship" and _has_scrap(c):
            scrappable.append(c)
    for c in getattr(p, "bases", []):
        if c.get("type") == "base" and _has_scrap(c):
            scrappable.append(c)

    if not scrappable:
        from starrealms.view import ui_common
        ui_common.ui_print("You have no bases to use and no ships with a scrap ability.")
        return

    from starrealms.view import ui_common
    ui_common.ui_print("Scrappable cards:")
    for i, c in enumerate(scrappable, 1):
        ui_common.ui_print(f"  {i}) {c.get('name','?')} ({c.get('type','?')})")

    sel = ui_common.ui_input("Pick a card to scrap (number) or 'x' to cancel: ").strip().lower()
    if sel in ("x", ""):
        return
    try:
        idx = int(sel) - 1
        card = scrappable[idx]
    except Exception:
        ui_common.ui_print("Invalid selection.")
        return

    if ui_common.ui_input(f"Scrap {card.get('name','?')}? (y/n): ").strip().lower() != "y":
        ui_common.ui_print("Canceled.")
        return

    ok = (p.activate_ship(card, o, g, scrap=True) if card.get("type") == "ship"
          else p.activate_base(card, o, g, scrap=True))
    if not ok:
        ui_common.ui_print("Could not scrap that card.")
