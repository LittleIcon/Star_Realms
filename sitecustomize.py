# Runtime shim: dedupe duplicate combat effects inside a single apply_effects call.
# Also includes a small guard to avoid double 'play' triggers if those exist elsewhere.
import os

def _dedupe_combat_effects(effs):
    """Return a new list with duplicate combat effects (same amount) removed, preserving order."""
    if not isinstance(effs, list):
        return effs
    seen = set()
    out = []
    for e in effs:
        try:
            t = e.get("type")
        except Exception:
            out.append(e); continue
        if t == "combat":
            amt = int(e.get("amount", 0) or 0)
            key = ("combat", amt)
            if key in seen:
                # skip duplicate combat entry
                continue
            seen.add(key)
        out.append(e)
    return out

try:
    # Wrap apply_effects to dedupe combat within each call
    from starrealms import effects as _effects
    _orig_apply_effects = _effects.apply_effects

    def _apply_effects_dedup(effs, player, opponent, game, **kwargs):
        effs = _dedupe_combat_effects(effs)
        return _orig_apply_effects(effs, player, opponent, game, **kwargs)

    _effects.apply_effects = _apply_effects_dedup
except Exception:
    pass

# Optional: guard for 'play' re-entry (harmless if not needed)
if os.environ.get("SR_GUARD_PLAY", "1") == "1":
    try:
        from starrealms.engine import unified_dispatcher as _ud
        _orig_trigger = _ud.UnifiedDispatcher.trigger
        def _guarded_trigger(self, trigger, **kwargs):
            card = kwargs.get("card")
            game = kwargs.get("game")
            if trigger in ("play","on_play") and isinstance(card, dict):
                turn = getattr(game, "turn_number", 0)
                k = "__play_done_turn__"
                if card.get(k) == turn:
                    return
                card[k] = turn
            return _orig_trigger(self, trigger, **kwargs)
        _ud.UnifiedDispatcher.trigger = _guarded_trigger
    except Exception:
        pass
