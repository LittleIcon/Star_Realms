#!/usr/bin/env python3
# tools/cards_tool.py
import argparse, json, sys, glob, os, pathlib

# ---- optional JSON Schema (very light; expand as you like) ----
SCHEMA = {
    "type": "object",
    "required": ["schema_version", "id", "name", "faction", "type", "abilities"],
    "properties": {
        "schema_version": {"type": "integer", "const": 2},
        "id": {"type": "integer"},
        "name": {"type": "string"},
        "faction": {"type": "string"},
        "type": {"type": "string"},
        "abilities": {"type": "array"},
    },
    "additionalProperties": True,  # loosen if you’re still iterating
}

try:
    from jsonschema import validate as _validate_schema
except Exception:
    _validate_schema = None

def _validate_card(card, path=None):
    # Always do a syntax/type sanity pass
    if not isinstance(card, dict):
        raise ValueError(f"{path or '<card>'}: not a JSON object")

    # Enforce minimal shape
    for k in SCHEMA["required"]:
        if k not in card:
            raise ValueError(f"{path or '<card>'}: missing required field '{k}'")

    # If jsonschema is available, do a formal validation
    if _validate_schema:
        _validate_schema(instance=card, schema=SCHEMA)

def load_cards_from_dir(folder):
    folder = pathlib.Path(folder)
    files = sorted(glob.glob(str(folder / "*.json")))
    cards = []
    for fp in files:
        with open(fp, "r", encoding="utf-8") as f:
            try:
                card = json.load(f)
            except json.JSONDecodeError as e:
                raise SystemExit(f"JSON error in {fp} at line {e.lineno}, col {e.colno}: {e.msg}") from e
        _validate_card(card, fp)
        cards.append(card)
    return cards, files

def write_unified(cards, out_path):
    out_path = pathlib.Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(cards, f, indent=2, ensure_ascii=False)
        f.write("\n")

def split_unified(in_path, out_dir):
    out_dir = pathlib.Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(in_path, "r", encoding="utf-8") as f:
        try:
            cards = json.load(f)
        except json.JSONDecodeError as e:
            raise SystemExit(f"JSON error in {in_path} at line {e.lineno}, col {e.colno}: {e.msg}") from e
    if not isinstance(cards, list):
        raise SystemExit(f"{in_path} must be a JSON array of card objects")

    for c in cards:
        _validate_card(c, in_path)
        cid = c.get("id", "unknown")
        name = c.get("name", "card").lower().replace(" ", "_").replace("/", "_")
        fp = out_dir / f"{cid:03d}_{name}.json"
        with open(fp, "w", encoding="utf-8") as f:
            json.dump(c, f, indent=2, ensure_ascii=False)
            f.write("\n")

def main():
    ap = argparse.ArgumentParser(description="Star Realms cards JSON helper")
    sub = ap.add_subparsers(dest="cmd", required=True)

    # validate
    ap_val = sub.add_parser("validate", help="Validate per-card JSON files in a directory")
    ap_val.add_argument("--dir", required=True, help="Directory of per-card JSON files (e.g. .../base_set/cards)")

    # merge
    ap_merge = sub.add_parser("merge", help="Merge per-card files into a unified JSON")
    ap_merge.add_argument("--dir", required=True, help="Directory of per-card JSON files")
    ap_merge.add_argument("--out", required=True, help="Output path for unified JSON (e.g. cards_unified.json)")

    # split
    ap_split = sub.add_parser("split", help="Split a unified JSON file into per-card files")
    ap_split.add_argument("--in", dest="inp", required=True, help="Unified JSON path")
    ap_split.add_argument("--outdir", required=True, help="Output directory for per-card files")

    args = ap.parse_args()

    if args.cmd == "validate":
        cards, files = load_cards_from_dir(args.dir)
        print(f"OK: {len(cards)} card file(s) validated in {args.dir}")
        if _validate_schema is None:
            print("(Tip: pip install jsonschema for stricter validation)")

    elif args.cmd == "merge":
        cards, _ = load_cards_from_dir(args.dir)
        # Keep deterministic order: id ascending (fallback to name)
        cards.sort(key=lambda c: (c.get("id", 10**9), c.get("name", "")))
        write_unified(cards, args.out)
        print(f"Wrote {len(cards)} cards to {args.out}")

    elif args.cmd == "split":
        split_unified(args.inp, args.outdir)
        print(f"Split cards from {args.inp} into {args.outdir}")

if __name__ == "__main__":
    main()