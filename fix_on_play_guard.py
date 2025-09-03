import re, os

path = "starrealms/engine/unified_dispatcher.py"
if not os.path.exists(path):
    raise SystemExit(f"File not found: {path}")

src = open(path, "r", encoding="utf-8").read()
out = src

# Add helper function if missing
if "_mark_play_once" not in out:
    helper = """
def _mark_play_once(card, turn_no):
    \"\"\"Ensure on_play effects run only once per card per turn.\"\"\"
    if not isinstance(card, dict):
        return True
    key = "__on_play_done_turn__"
    if card.get(key) == turn_no:
        return False
    card[key] = turn_no
    return True
"""
    out = out.replace("import", "import", 1) + helper  # append helper at end of imports

# Inject guard into the first on_play branch
pattern = r'(\bif\s+trigger\s*==\s*[\'"]on_play[\'"]\s*:)'
replacement = (
    r"\1\n"
    r"            turn_no = getattr(game, 'turn_number', 0)\n"
    r"            if not _mark_play_once(card, turn_no):\n"
    r"                return"
)
out, n = re.subn(pattern, replacement, out, count=1)

if n:
    with open(path, "w", encoding="utf-8") as f:
        f.write(out)
    print(f"Patched {path} (guard inserted).")
else:
    print("No on_play branch matched; nothing changed.")
