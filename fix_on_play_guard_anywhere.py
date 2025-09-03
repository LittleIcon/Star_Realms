import os, re, sys

def patch_unified_dispatcher(path):
    if not os.path.exists(path):
        return False, f"missing {path}"
    s = open(path, "r", encoding="utf-8").read()
    if "__on_play_done_turn__" in s:
        return True, "already patched"

    # Insert a generic guard at the TOP of UnifiedDispatcher.trigger(...)
    # Works whether you use trigger == "on_play" or "play" elsewhere.
    pat = re.compile(r'(\n\s*def\s+trigger\s*\([^)]*\):\s*\n)', re.DOTALL)
    m = pat.search(s)
    if not m:
        return False, "no trigger() def found"

    guard = (
        m.group(1) +
        "        # One-shot guard for on-play (aka 'play') effects\n"
        "        if trigger in ('on_play', 'play'):\n"
        "            turn_no = getattr(game, 'turn_number', 0)\n"
        "            if isinstance(card, dict):\n"
        "                key = '__on_play_done_turn__'\n"
        "                if card.get(key) == turn_no:\n"
        "                    return\n"
        "                card[key] = turn_no\n"
    )
    s2 = s[:m.start()] + guard + s[m.end():]
    open(path, "w", encoding="utf-8").write(s2)
    return True, "patched trigger guard"

def patch_player_play_card(path):
    if not os.path.exists(path):
        return False, f"missing {path}"
    s = open(path, "r", encoding="utf-8").read()
    if "__on_play_done_turn__" in s:
        return True, "already patched"

    # Find def play_card(...):
    m = re.search(r'(\n\s*def\s+play_card\s*\(.*\):\s*\n)', s)
    if not m:
        return False, "no play_card() found"

    # We'll inject a small guard and wrap the dispatcher call if we can find it.
    inject_after_def = (
        m.group(1) +
        "        # Guard to avoid double on_play firing per physical card per turn\n"
        "        turn_no = getattr(game, 'turn_number', 0)\n"
        "        _on_play_ok = True\n"
        "        if isinstance(card, dict):\n"
        "            key = '__on_play_done_turn__'\n"
        "            if card.get(key) == turn_no:\n"
        "                _on_play_ok = False\n"
        "            else:\n"
        "                card[key] = turn_no\n"
    )
    s = s[:m.start()] + inject_after_def + s[m.end():]

    # Wrap dispatcher trigger call(s) for on_play/play
    # Replace lines like: game.dispatcher.trigger("on_play", ...)  -> if _on_play_ok: game.dispatcher.trigger(...)
    s, n1 = re.subn(
        r'(\bdispatcher\.trigger\s*\(\s*[\'"]on_play[\'"]\s*,)',
        r'if _on_play_ok: \n            \1',
        s
    )
    s, n2 = re.subn(
        r'(\bdispatcher\.trigger\s*\(\s*[\'"]play[\'"]\s*,)',
        r'if _on_play_ok: \n            \1',
        s
    )

    open(path, "w", encoding="utf-8").write(s)
    return True, f"patched play_card guard; wrapped {n1+n2} dispatcher call(s)"

def main():
    ud = "starrealms/engine/unified_dispatcher.py"
    ok, msg = patch_unified_dispatcher(ud)
    print(f"{ud}: {msg}")
    if not ok:
        # Fallback to player.py
        pp = "starrealms/player.py"
        ok2, msg2 = patch_player_play_card(pp)
        print(f"{pp}: {msg2}")
        if not ok2:
            sys.exit(1)

if __name__ == "__main__":
    main()
