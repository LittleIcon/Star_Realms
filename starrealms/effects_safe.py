# starrealms/effects_safe.py
from inspect import signature

def _call_with_accepted_kwargs(fn, **kwargs):
    params = signature(fn).parameters
    return fn(**{k: v for k, v in kwargs.items() if k in params})

def run_effects_safe(game, actor, opponent, effects):
    if not effects:
        return
    if hasattr(game, "apply_effects") and callable(getattr(game, "apply_effects")):
        _call_with_accepted_kwargs(game.apply_effects,
                                   effects=effects, actor=actor, opponent=opponent, game=game)
        return
    if hasattr(actor, "apply_effects") and callable(getattr(actor, "apply_effects")):
        _call_with_accepted_kwargs(actor.apply_effects,
                                   effects=effects, actor=actor, opponent=opponent, game=game)
        return
    # Minimal fallback (only used if neither exists)
    for e in effects:
        t, n = e.get("type"), int(e.get("amount", 0) or 0)
        if t == "combat":    actor.combat_pool += n
        elif t == "trade":   actor.trade_pool += n
        elif t == "authority": actor.authority += n