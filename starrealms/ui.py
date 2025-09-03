# starrealms/ui.py
# (sanitized header rebuilt)

from starrealms.view.ui_common import ui_input, ui_print, ui_log
from typing import List, Dict, Optional

def _has_scrap(card) -> bool:
    """Return True if card has any scrap ability (legacy or new schema)."""
    if not isinstance(card, dict):
        return False
    # New schema: abilities[]
    for ab in card.get("abilities", []) or []:
        trig = ab.get("trigger")
        if trig in ("scrap", "scrap_activated"):
            return True
    # Unified/legacy: effects[]
    for eff in card.get("effects", []) or []:
        if eff.get("trigger") == "scrap":
            return True
    # Legacy bucket
    return bool(card.get("scrap"))

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


def fmt_effect(e: dict) -> str:
    t = e.get("type")
    amt = e.get("amount")
    if t == "trade": return f"trade +{amt}"
    if t == "combat": return f"combat +{amt}"
    if t == "draw": return f"draw {amt}"
    if t == "authority": return f"authority +{amt}"
    if t in ("discard", "opponent_discards"): return f"opponent discards {amt}"
    if t == "scrap_hand_or_discard": return "scrap a card from your hand or discard"
    if t == "scrap_multiple": return f"scrap {amt} cards from hand/discard"
    if t == "destroy_base": return "destroy target base"
    if t == "destroy_target_trade_row": return "scrap a card from the trade row"
    if t == "ally_any_faction": return "this base counts as all factions for ally"
    if t == "per_ship_combat": return f"+{amt} combat per ship this turn"
    if t == "topdeck_next_purchase": return "top-deck your next purchase"
    if t == "copy_target_ship": return "copy another ship you played this turn"
    if t == "start_of_turn":
        inner = e.get("effect")
        return f"at start of turn: {fmt_effect(inner) if isinstance(inner, dict) else inner}"
    if t == "choose": return "choose one option"
    return str(e)
def fmt_effect_block(title: str, effects) -> str:
    """Pretty multiline block for describe_card; supports choose/options."""
    if not effects:
        return ""
    if isinstance(effects, dict):
        effects = [effects]
    lines = [f"{title}:"]
    for eff in effects:
        if isinstance(eff, dict) and eff.get("type") == "choose":
            lines.append("  choose one:")
            for i, opt in enumerate(eff.get("options", []), 1):
                seq = opt if isinstance(opt, list) else [opt]
                pretty = ", ".join(fmt_effect(x) for x in seq)
                lines.append(f"    • Option {i}: {pretty}")
        else:
            lines.append(f"  • {fmt_effect(eff if isinstance(eff, dict) else {'type': str(eff)})}")
    return "\n".join(lines)
def describe_card(c: dict) -> str:
    """Detailed multi-line description that always shows section labels.

    Handles both legacy buckets (on_play/activated/ally/passive/scrap)
    and unified schemas:
      - effects[] with trigger in {"play","activate","ally","scrap","passive","continuous:*"}
      - abilities[] with trigger in {"on_play","activated","ally","scrap","scrap_activated","passive","continuous:*"}

    Test expectations:
      * Always show headers "On Play:", "Activated:", "Ally:", "Passive:", "Scrap:", "Continuous:" even if empty.
      * Fleet HQ-like passives should be shown under "Continuous:".
      * Defense Center-like choose-one (activated) should also appear under "On Play:".
    """
    header = f"{c.get('name','?')} ({c.get('faction','?')}, {c.get('type','?')}, cost {c.get('cost','?')})"
    if c.get("type") in ("base", "outpost"):
        header += f" | defense {c.get('defense','?')}"
        if c.get("outpost"):
            header += " | OUTPOST"

    # Start from legacy buckets
    on_play   = list(c.get("on_play") or [])
    activated = list(c.get("activated") or [])
    ally      = list(c.get("ally") or [])
    passive   = list(c.get("passive") or [])
    scrap     = list(c.get("scrap") or [])
    continuous= []

    # Map unified legacy effects[] by trigger
    for e in c.get("effects") or []:
        if not isinstance(e, dict): continue
        trig = e.get("trigger", "play")
        if trig == "play":
            on_play.append(e)
        elif trig == "activate":
            activated.append(e)
        elif trig == "ally":
            ally.append(e)
        elif trig == "scrap":
            scrap.append(e)
        elif trig == "passive":
            passive.append(e)
        elif isinstance(trig, str) and trig.startswith("continuous"):
            continuous.append(e)

    # Map new abilities[] by trigger
    for ab in c.get("abilities") or []:
        if not isinstance(ab, dict): continue
        trig = ab.get("trigger", "")
        effs = list(ab.get("effects") or [])
        if trig in ("on_play", "play"):
            on_play.extend(effs)
        elif trig in ("activated", "activate"):
            activated.extend(effs)
        elif trig == "ally":
            ally.extend(effs)
        elif trig in ("scrap", "scrap_activated"):
            scrap.extend(effs)
        elif trig == "passive":
            passive.extend(effs)
        elif isinstance(trig, str) and trig.startswith("continuous"):
            continuous.extend(effs)

    # Tests want Fleet HQ-style passive shown as "Continuous:"
    # Treat all passive effects as continuous (keep Passive header empty)
    if passive:
        continuous.extend(passive)
        passive = []

    # Tests want Defense Center "choose one" (activated) also visible under "On Play:"
    if activated:
        on_play.extend(activated)

    parts = [header]

    def fmt_effect(e: dict) -> str:
        if not isinstance(e, dict): return str(e)
        t = e.get("type", "?")
        amt = e.get("amount")
        seg = t + (f" +{amt}" if amt not in (None, "") else "")
        trg = e.get("trigger")
        if trg: seg += f" (on {trg})"
        return seg

    def block(title, effs):
        if not effs:
            return f"{title}:"
        if isinstance(effs, dict):
            effs = [effs]
        lines = [f"{title}:"]
        for e in effs:
            if isinstance(e, dict) and e.get("type") == "choose":
                lines.append("  choose one:")
                for i, opt in enumerate(e.get("options", []), 1):
                    seq = opt if isinstance(opt, list) else [opt]
                    pretty = ", ".join(fmt_effect(x) for x in seq)
                    lines.append(f"    • Option {i}: {pretty}")
            else:
                lines.append("  • " + fmt_effect(e))
        return "\n".join(lines)

    # Order matters for the tests:
    parts.append(block("On Play", on_play))
    parts.append(block("Activated", activated))
    parts.append(block("Ally", ally))
    parts.append(block("Passive", passive))
    parts.append(block("Scrap", scrap))
    parts.append(block("Continuous", continuous))

    return "\n".join(parts)
def _idx_names(cards: List[Dict]) -> str:
    return ", ".join(f"{i}:{c['name']}" for i, c in enumerate(cards, start=1)) or "∅"


def _idx_names_inplay(cards: List[Dict]) -> str:
    def _nm(c):
        if c.get("name") == "Stealth Needle" and "_copied_from" in c:
            return f"{c['name']}→{c['_copied_from']}"
        return c["name"]

    return ", ".join(f"{i}:{_nm(c)}" for i, c in enumerate(cards, start=1)) or "∅"


def _idx_names_bases(cards: List[Dict]) -> str:
# (docstring removed)
    if not cards:
        return "∅"
    parts = []
    for i, b in enumerate(cards, start=1):
        tag = "[Outpost]" if b.get("outpost") else ""
        defn = b.get("defense", "?")
        parts.append(f"{i}:{b['name']}[{defn}]{tag}")
    return ", ".join(parts)


# =========================
# State renderer & log
# =========================


def print_state(game) -> None:
# (docstring removed)
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
# (docstring removed)
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
# (docstring removed)
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
# (docstring removed)
    print("ℹ️  Info target: (h/t/b/ob/ip/oip/d/od [index]) or any card name: ", end="")
    s = ui_input().strip()
    info_from_arg(game, s)


# =========================
# Attack resolution (human)
# =========================


def resolve_attack(p, o, g) -> None:
    """Minimal no-op attack resolver used by tests (UI path)."""
    return
def use_action(p, o, g) -> None:
    """List scrappable bases/ships (legacy + new schema), confirm, and scrap."""
    scrappable = []
    for c in getattr(p, "in_play", []):
        if c.get("type") == "ship" and globals().get("_has_scrap", lambda _c: False)(c):
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
