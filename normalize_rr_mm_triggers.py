import json, os, glob

NAMES = {"Royal Redoubt": 3, "Missile Mech": 6}  # desired +combat on play

def load(p):
    try:
        with open(p, "r", encoding="utf-8") as f: return json.load(f)
    except Exception: return None

def save(p, data):
    with open(p, "w", encoding="utf-8") as f: json.dump(data, f, indent=2, sort_keys=True)

def card_list(doc):
    if isinstance(doc, list): return doc, ("list", None)
    if isinstance(doc, dict):
        if isinstance(doc.get("cards"), list): return doc["cards"], ("cards", doc)
        if "name" in doc: return [doc], ("single", doc)
    return None, (None, None)

def fix_card(c):
    name = c.get("name")
    if name not in NAMES: return False
    changed = False
    want = NAMES[name]

    # 1) Fix abilities: any *_ally ability must have trigger 'ally'
    ab = c.get("abilities")
    if isinstance(ab, list):
        for a in ab:
            if isinstance(a.get("id"), str) and a["id"].endswith("_ally"):
                if a.get("trigger") != "ally":
                    a["trigger"] = "ally"
                    changed = True

    # 2) Normalize effects to ONE 'play' combat (amount=want) and, for Missile Mech, ONE 'play' destroy_base
    eff = c.get("effects")
    if not isinstance(eff, list):
        eff = []
    keep = []
    seen_play_combat = False
    seen_play_destroy = False
    for e in eff:
        trig = e.get("trigger")
        typ  = e.get("type")
        amt  = int(e.get("amount", 0) or 0)

        # Convert any 'on_play' to 'play' (schema expects 'play')
        if trig == "on_play":
            e["trigger"] = "play"
            trig = "play"
            changed = True

        # Ally rules
        if trig == "ally":
            # Missile Mech ally draw must be 1; Royal Redoubt ally is opponent_discards 1
            if name == "Missile Mech" and typ == "draw" and amt != 1:
                e["amount"] = 1
                changed = True
            keep.append(e)
            continue

        # Collapse play combat to single entry with desired amount
        if trig == "play" and typ == "combat":
            if seen_play_combat:
                changed = True
                continue
            if amt != want:
                e["amount"] = want
                changed = True
            keep.append(e)
            seen_play_combat = True
            continue

        # Missile Mech: keep one destroy_base on play
        if name == "Missile Mech" and trig == "play" and typ == "destroy_base":
            if seen_play_destroy:
                changed = True
                continue
            keep.append(e)
            seen_play_destroy = True
            continue

        # Drop any draw mistakenly on play
        if trig == "play" and typ == "draw":
            changed = True
            continue

        # keep everything else
        keep.append(e)

    # 3) Migrate & clear legacy on_play array (treat as 'play' per schema)
    onp = c.get("on_play")
    if isinstance(onp, list) and onp:
        for e in onp:
            typ = e.get("type")
            amt = int(e.get("amount", 0) or 0)
            if typ == "combat" and not any(x.get("trigger")=="play" and x.get("type")=="combat" for x in keep):
                keep.append({"trigger":"play","type":"combat","amount": want})
                changed = True
            if name == "Missile Mech" and typ == "destroy_base" and not any(x.get("trigger")=="play" and x.get("type")=="destroy_base" for x in keep):
                keep.append({"trigger":"play","type":"destroy_base"})
                changed = True
        c["on_play"] = []
        changed = True

    if c.get("effects") != keep:
        c["effects"] = keep
        changed = True

    return changed

def process(path):
    data = load(path)
    if data is None: return False
    cards, kind = card_list(data)
    if cards is None: return False
    touched = False
    for c in cards:
        touched |= fix_card(c)
    if touched:
        if kind[0] == "cards":
            kind[1]["cards"] = cards
            save(path, kind[1])
        elif kind[0] == "single":
            save(path, cards[0])
        else:
            save(path, cards)
        print(f"{path}: fixed")
    return touched

def main():
    any_touched = False
    for p in sorted(set(glob.glob("starrealms/cards/**/*.json", recursive=True))):
        if process(p):
            any_touched = True
    if not any_touched:
        print("No changes needed.")
main()
