import json, os, glob

def load(p):
    try:
        with open(p, "r", encoding="utf-8") as f: return json.load(f)
    except Exception: return None

def save(p, data):
    with open(p, "w", encoding="utf-8") as f: json.dump(data, f, indent=2, sort_keys=True)

def as_list(doc):
    if isinstance(doc, list): return doc, ("list", None)
    if isinstance(doc, dict):
        if isinstance(doc.get("cards"), list): return doc["cards"], ("dict_cards", doc)
        if "name" in doc: return [doc], ("single", doc)
    return None, (None, None)

def fix(doc):
    cards, (kind, parent) = as_list(doc)
    if cards is None: return False, None, None
    changed = 0
    for c in cards:
        ab = c.get("abilities")
        if not isinstance(ab, list): continue
        for a in ab:
            # Any ally ability (id ends with _ally) must have trigger 'ally'
            if isinstance(a.get("id"), str) and a["id"].endswith("_ally"):
                if a.get("trigger") != "ally":
                    a["trigger"] = "ally"
                    changed += 1
    if changed:
        if kind == "dict_cards":
            parent["cards"] = cards
            return True, parent, kind
        elif kind == "single":
            return True, cards[0], kind
        else:
            return True, cards, kind
    return False, None, None

roots = ["starrealms/cards", "starrealms/cards/standalone/base_set"]
touched = 0
for root in roots:
    for p in sorted(set(glob.glob(os.path.join(root, "**/*.json"), recursive=True))):
        data = load(p)
        if data is None: 
            continue
        ch, newdoc, kind = fix(data)
        if ch:
            save(p, newdoc)
            print(f"{p}: fixed ally ability trigger(s)")
            touched += 1
print(f"Done. Files updated: {touched}")
