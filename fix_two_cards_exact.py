import json, os, sys, glob

TARGETS = ["Missile Mech", "Royal Redoubt"]

def load_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=True)

def as_card_list(doc):
    # file may be: list of cards, dict with 'cards', or single card dict
    if isinstance(doc, list):
        return doc, ("list", None)
    if isinstance(doc, dict):
        if isinstance(doc.get("cards"), list):
            return doc["cards"], ("dict_cards", doc)
        if "name" in doc:
            return [doc], ("single", doc)
    return None, (None, None)

def fix_mm(card):
    """
    Missile Mech: ensure exactly ONE on-play +6 combat and ONE destroy_base on-play;
    ally draw must be exactly 1; remove duplicate on_play array and wrong triggers.
    """
    changed = False

    # 1) Fix abilities trigger for ally blocks mislabeled as on_play
    for a in card.get("abilities", []):
        if a.get("id","").endswith("_ally") and a.get("trigger") != "ally":
            a["trigger"] = "ally"
            changed = True

    # 2) Normalize effects: collapse 'play'/'on_play' combat/destroy_base into single on_play entries
    eff = card.get("effects", [])
    if not isinstance(eff, list):
        eff = []
    keep = []
    kept_onplay_combat = False
    kept_onplay_destroy = False
    for e in eff:
        trig = e.get("trigger")
        typ  = e.get("type")
        amt  = int(e.get("amount", 0) or 0)

        # Ally draw must be 1
        if trig == "ally" and typ == "draw":
            if amt != 1:
                e["amount"] = 1
                changed = True
            keep.append(e)
            continue

        # Collapse play/on_play combat to single on_play +6
        if typ == "combat" and trig in ("play", "on_play"):
            if not kept_onplay_combat:
                e["trigger"] = "on_play"
                e["amount"] = 6
                keep.append(e)
                kept_onplay_combat = True
                if trig != "on_play" or amt != 6:
                    changed = True
            else:
                changed = True
            continue

        # Collapse destroy_base to single on_play
        if typ == "destroy_base" and trig in ("play", "on_play"):
            if not kept_onplay_destroy:
                e["trigger"] = "on_play"
                keep.append(e)
                kept_onplay_destroy = True
                if trig != "on_play":
                    changed = True
            else:
                changed = True
            continue

        # Drop any on_play draw (shouldn’t exist here)
        if trig in ("play","on_play") and typ == "draw":
            changed = True
            continue

        keep.append(e)
    eff = keep

    # 3) Also migrate/remove legacy on_play array duplicates
    onp = card.get("on_play")
    if isinstance(onp, list):
        for e in onp:
            typ = e.get("type")
            if typ == "combat":
                if not any(x.get("type")=="combat" and x.get("trigger")=="on_play" for x in eff):
                    eff.append({"trigger":"on_play","type":"combat","amount":6})
                    changed = True
            elif typ == "destroy_base":
                if not any(x.get("type")=="destroy_base" and x.get("trigger")=="on_play" for x in eff):
                    eff.append({"trigger":"on_play","type":"destroy_base"})
                    changed = True
            # ignore on_play draw if present
        # remove legacy array to avoid double-firing
        if onp:
            card["on_play"] = []
            changed = True

    # 4) Persist effects back
    if card.get("effects") != eff:
        card["effects"] = eff
        changed = True

    return changed

def fix_rr(card):
    """
    Royal Redoubt: ensure exactly ONE on-play +3 combat; ally discard remains ally;
    remove any activated +3; remove on_play array duplicates; fix mis-labeled triggers.
    """
    changed = False

    # 1) Fix abilities trigger for ally blocks mislabeled as on_play
    for a in card.get("abilities", []):
        if a.get("id","").endswith("_ally") and a.get("trigger") != "ally":
            a["trigger"] = "ally"
            changed = True

    # 2) Strip any activated +3 combat
    def strip_activated(arr):
        nonlocal changed
        if not isinstance(arr, list): return arr
        keep = []
        for e in arr:
            if e.get("trigger")=="activated" and e.get("type")=="combat" and int(e.get("amount",0))==3:
                changed = True
                continue
            keep.append(e)
        return keep

    if isinstance(card.get("effects"), list):
        card["effects"] = strip_activated(card["effects"])
    if isinstance(card.get("scrap"), list):
        card["scrap"] = strip_activated(card["scrap"])

    # 3) Normalize effects: collapse 'play'/'on_play' combat to single on_play +3
    eff = card.get("effects", [])
    if not isinstance(eff, list):
        eff = []
    keep = []
    kept_onplay_combat = False
    for e in eff:
        trig = e.get("trigger")
        typ  = e.get("type")
        amt  = int(e.get("amount", 0) or 0)

        # Ally discard should stay as ally
        if typ == "opponent_discards" and trig == "ally":
            keep.append(e)
            continue

        if typ == "combat" and trig in ("play", "on_play"):
            if not kept_onplay_combat:
                e["trigger"] = "on_play"
                e["amount"] = 3
                keep.append(e)
                kept_onplay_combat = True
                if trig != "on_play" or amt != 3:
                    changed = True
            else:
                changed = True
            continue

        # Drop any on_play draw (shouldn’t exist)
        if trig in ("play","on_play") and typ == "draw":
            changed = True
            continue

        keep.append(e)
    eff = keep

    # 4) Migrate/remove legacy on_play duplicates
    onp = card.get("on_play")
    if isinstance(onp, list):
        for e in onp:
            if e.get("type") == "combat":
                if not any(x.get("type")=="combat" and x.get("trigger")=="on_play" for x in eff):
                    eff.append({"trigger":"on_play","type":"combat","amount":3})
                    changed = True
        if onp:
            card["on_play"] = []
            changed = True

    if card.get("effects") != eff:
        card["effects"] = eff
        changed = True

    return changed

def fix_card(card):
    if card.get("name") == "Missile Mech":
        return fix_mm(card)
    if card.get("name") == "Royal Redoubt":
        return fix_rr(card)
    return False

def process_file(path):
    data = load_json(path)
    if data is None:
        print(f"{path}: unreadable or missing")
        return
    cards, (kind, parent) = as_card_list(data)
    if cards is None:
        print(f"{path}: unknown structure")
        return
    touched = 0
    for c in cards:
        if c.get("name") in TARGETS:
            if fix_card(c):
                touched += 1
    if touched:
        if kind == "dict_cards":
            parent["cards"] = cards
            save_json(path, parent)
        elif kind == "single":
            save_json(path, cards[0])
        else:
            save_json(path, cards)
        print(f"{path}: updated ({touched} card(s))")
    else:
        print(f"{path}: no changes")

def main():
    # Search likely files
    candidates = []
    roots = ["starrealms/cards/standalone/base_set", "starrealms/cards"]
    for root in roots:
        for p in glob.glob(os.path.join(root, "**/*.json"), recursive=True):
            candidates.append(p)
    seen = set()
    for p in sorted(set(candidates)):
        process_file(p)

if __name__ == "__main__":
    main()
