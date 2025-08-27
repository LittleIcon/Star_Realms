# starrealms/display.py
"""
Display and formatting helpers for Star Realms.
Separates all printing from game logic.
"""

def fmt_effect(e):
    t = e.get("type")
    amt = e.get("amount")
    if t == "trade": return f"trade +{amt}"
    if t == "combat": return f"combat +{amt}"
    if t == "draw": return f"draw {amt}"
    if t == "authority": return f"authority +{amt}"
    if t == "discard": return f"opponent discards {amt}"
    if t == "scrap_hand_or_discard": return "scrap a card from your hand or discard"
    if t == "scrap_multiple": return f"scrap {amt} cards from hand/discard"
    if t == "destroy_base": return "destroy target base"
    if t == "destroy_target_trade_row": return "scrap a card from the trade row"
    if t == "ally_any_faction": return "this base counts as all factions for ally"
    if t == "per_ship_combat": return f"+{amt} combat for each ship you play this turn"
    if t == "topdeck_next_purchase": return "top-deck your next purchase"
    if t == "copy_target_ship": return "copy another ship you played this turn"
    if t == "choose": return "choose one option"
    return str(e)

def fmt_effect_block(title, effects):
    if not effects:
        return ""
    if isinstance(effects, dict):  # safety
        effects = [effects]
    lines = [f"{title}:"]
    for eff in effects:
        if isinstance(eff, dict) and eff.get("type") == "choose":
            lines.append("  choose one:")
            options = eff.get("options", [])
            for i, opt in enumerate(options, 1):
                if isinstance(opt, dict):
                    opt = [opt]
                pretty = ", ".join(fmt_effect(x) for x in opt)
                lines.append(f"    • Option {i}: {pretty}")
        else:
            lines.append(f"  • {fmt_effect(eff)}")
    return "\n".join(lines)

def describe_card(c):
    header = f"{c['name']} ({c['faction']}, {c['type']}, cost {c['cost']})"
    if c["type"] in ("base", "outpost", "base"):
        header += f" | defense {c.get('defense','?')}"
        if c.get("outpost"):
            header += " | OUTPOST"

    parts = [header]

    if c.get("name") == "Stealth Needle" and "_copied_from" in c:
        parts.append(f"(Copied this turn from: {c['_copied_from']})")

    parts.append(fmt_effect_block("Effects", c.get("effects", [])))
    parts.append(fmt_effect_block("Ally", c.get("ally", [])))
    parts.append(fmt_effect_block("Scrap", c.get("scrap", [])))

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
        parts.append(fmt_effect_block("Conditional effects", cond.get("effects", [])))
    return "\n".join(p for p in parts if p)

def print_state(game):
    p = game.current_player()
    o = game.opponent()

    def _idx_names(cards):
        return ", ".join(f"{i+1}:{c['name']}" for i, c in enumerate(cards)) or "∅"

    def _idx_names_inplay(cards):
        def _nm(c):
            if c.get("name") == "Stealth Needle" and "_copied_from" in c:
                return f"{c['name']}→{c['_copied_from']}"
            return c["name"]
        return ", ".join(f"{i+1}:{_nm(c)}" for i, c in enumerate(cards)) or "∅"

    trade_row_str = ", ".join(
        f"{i+1}:{c['name']}({c['cost']})" for i, c in enumerate(game.trade_row)
    ) or "∅"

    def _deck_len(pl):     return len(getattr(pl, "deck", []))
    def _discard_len(pl):  return len(getattr(pl, "discard_pile", getattr(pl, "discard", [])))
    def _hand_len(pl):     return len(getattr(pl, "hand", []))

    print("\n==============================")
    print(f"🕒 TURN {game.turn_number}: {p.name}")
    print("------------------------------")
    print(f"👤 {p.name}: 💚 {p.authority}  |  🟡 {p.trade_pool}  |  🔺 {p.combat_pool}")
    print(f"📦 Deck: {_deck_len(p)}  |  🗑️ Discard: {_discard_len(p)}  |  ✋ Hand: {_hand_len(p)}")
    print(f"🃏 Hand cards: [{_idx_names(p.hand)}]")
    print(f"🚀 In Play: [{_idx_names_inplay(p.in_play)}]")
    print(f"🏰 Bases: [{_idx_names(p.bases)}]")
    print("")
    print(f"👤 {o.name}: 💚 {o.authority}")
    print(f"📦 Deck: {_deck_len(o)}  |  🗑️ Discard: {_discard_len(o)}  |  ✋ Hand: {_hand_len(o)}")
    print(f"🚀 {o.name} In Play: [{_idx_names_inplay(o.in_play)}]")
    print(f"🏰 {o.name} Bases: [{_idx_names(o.bases)}]")
    print("")
    print(f"🛒 Trade Row: [{trade_row_str}]  |  ✨ Explorer(2)")
    print("==============================")