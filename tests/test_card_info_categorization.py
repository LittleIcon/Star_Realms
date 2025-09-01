# tests/test_card_info_categorization.py
from starrealms.cards import get_card_by_name
from starrealms.game import Game

def _categorize(card: dict) -> dict[str, list[str]]:
    """
    Classify abilities into 'On Play', 'Continuous', 'Ally', and 'Scrap' buckets,
    returning short, human-readable lines for each effect.
    """
    buckets = {"On Play": [], "Continuous": [], "Ally": [], "Scrap": []}

    # Helper to pretty-print a single effect dict
    def fmt(e: dict) -> str:
        t = e.get("type")
        a = e.get("amount")
        if t == "trade":        return f"trade +{a}"
        if t == "combat":       return f"combat +{a}"
        if t == "authority":    return f"authority +{a}"
        if t == "draw":         return f"draw {a}"
        if t == "topdeck_next_purchase" or t == "topdeck_next_purchase".replace("_", ""):
            return "top-deck next purchase"
        if t == "topdeck_next_purchase" or t == "topdeck_next_purchase".replace("_", ""):
            return "top-deck next purchase"
        if t == "topdeck_next_purchase" or t == "topdeck_next_purchase".replace("_", ""):
            return "top-deck next purchase"
        if t == "topdeck_next_purchase": return "top-deck next purchase"
        if t == "topdeck_next_purchase".replace("_",""): return "top-deck next purchase"
        if t == "topdeck_next_purchase": return "top-deck next purchase"
        if t == "topdeck_next_purchase": return "top-deck next purchase"
        if t == "topdeck_next_purchase": return "top-deck next purchase"
        if t == "topdeck_next_purchase": return "top-deck next purchase"
        if t == "topdeck_next_purchase": return "top-deck next purchase"
        if t == "topdeck_next_purchase": return "top-deck next purchase"
        if t == "topdeck_next_purchase": return "top-deck next purchase"
        if t == "topdeck_next_purchase": return "top-deck next purchase"
        if t == "topdeck_next_purchase": return "top-deck next purchase"
        if t == "topdeck_next_purchase": return "top-deck next purchase"
        if t == "topdeck_next_purchase": return "top-deck next purchase"
        if t == "topdeck_next_purchase": return "top-deck next purchase"
        if t == "destroy_base": return "destroy a base"
        if t == "destroy_target_trade_row": return "scrap from trade row"
        if t == "scrap_hand_or_discard": return "scrap from hand/discard"
        if t == "topdeck_next_purchase": return "top-deck next purchase"
        # Fallback
        return t or "effect"

    # New schema: explicit 'on_play'
    if isinstance(card.get("on_play"), list):
        for e in card["on_play"]:
            if isinstance(e, dict):
                buckets["On Play"].append(fmt(e))

    # Unified 'abilities' list with triggers/frequency/etc
    for ab in card.get("abilities", []) or []:
        trig = ab.get("trigger")
        effs = ab.get("effects") or []
        if not isinstance(effs, list):
            effs = [effs]

        # Continuous hook (e.g., Fleet HQ)
        if isinstance(trig, str) and trig.startswith("continuous:"):
            for e in effs:
                if isinstance(e, dict):
                    buckets["Continuous"].append(fmt(e))
            continue

        # Ally (condition with faction_in_play ...)
        cond = ab.get("condition") or {}
        if "faction_in_play" in cond or "faction_in_play" in str(cond):
            for e in effs:
                if isinstance(e, dict):
                    buckets["Ally"].append(fmt(e))
            continue

        # Scrapability: trigger "scrap_activated"
        if trig == "scrap_activated":
            for e in effs:
                if isinstance(e, dict):
                    buckets["Scrap"].append(fmt(e))
            continue

        # Activated (once_per_turn) that happens when you “use” the base/ship — we treat as On Play for display
        if trig == "activated":
            for e in effs:
                if isinstance(e, dict):
                    if e.get("type") == "choose_one" and isinstance(e.get("options"), list):
                        # flatten choose_one options into readable bits
                        for opt in e["options"]:
                            for sub in opt.get("effects", []):
                                if isinstance(sub, dict):
                                    buckets["On Play"].append(fmt(sub))
                    else:
                        buckets["On Play"].append(fmt(e))
            continue

        # Legacy shapes: effects with missing/“on_play” semantics
        if trig in (None, "on_play", "play"):
            for e in effs:
                if isinstance(e, dict):
                    buckets["On Play"].append(fmt(e))

    return buckets

def _render(card: dict) -> str:
    b = _categorize(card)
    lines = [f"{card['name']} ({card['faction']}, {card['type']}, cost {card['cost']})"]
    for section in ("On Play", "Continuous", "Ally", "Scrap"):
        items = b[section]
        if items:
            lines.append(f"{section}:")
            for eff in items:
                lines.append(f"  • {eff}")
    return "\n".join(lines)

def test_info_explorer_has_on_play_and_scrap_labels():
    g = Game(("P1","P2"))
    explorer = get_card_by_name(g.trade_deck + g.card_db, "Explorer")
    info = _render(explorer)
    # On Play: +2 trade
    assert "On Play:" in info
    assert "trade +2" in info
    # Scrap: +2 combat
    assert "Scrap:" in info
    assert "combat +2" in info

def test_info_blob_carrier_on_play_and_ally_labels():
    g = Game(("P1","P2"))
    card = get_card_by_name(g.trade_deck + g.card_db, "Blob Carrier")
    info = _render(card)
    # On Play: +7 combat
    assert "On Play:" in info
    assert "combat +7" in info
    # Ally: top-deck next purchase
    assert "Ally:" in info
    assert "top-deck next purchase" in info

def test_info_fleet_hq_shows_continuous_bonus():
    g = Game(("P1","P2"))
    card = get_card_by_name(g.trade_deck + g.card_db, "Fleet HQ")
    info = _render(card)
    assert "Continuous:" in info
    assert "combat +1" in info  # per ship played

def test_info_defense_center_flattens_choose_one_options():
    g = Game(("P1","P2"))
    card = get_card_by_name(g.trade_deck + g.card_db, "Defense Center")
    info = _render(card)
    # It’s an activated base with choose-one: (+2 combat & +3 authority) OR (+4 combat)
    # We just require the options’ effects appear under On Play.
    assert "On Play:" in info
    assert "combat +2" in info
    assert "authority +3" in info
    assert "combat +4" in info