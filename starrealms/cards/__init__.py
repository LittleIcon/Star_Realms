# starrealms/cards/__init__.py
from importlib import import_module
import logging
from typing import List, Dict, Any, Tuple

# Enable whatever sets you want here. Later, you can make this configurable.
ENABLED_SETS = [
    "standalone.base_set",
]

CARDS: List[Dict[str, Any]] = []
EXPLORER_NAME = "Explorer"
_modules = []  # keep the loaded set modules for deck building
_logger = logging.getLogger("starrealms.cards")


# --- Minimal normalization & validation (no external deps) --------------------


def _as_int(x, default=0) -> int:
    try:
        return int(x)
    except Exception:
        return default


def _copy_effect_fields(e: Dict[str, Any]) -> Dict[str, Any]:
    """
    Copy all commonly-used effect fields, including options for 'choose'.
    We ignore any incoming 'trigger' so callers can set it explicitly.
    """
    if not isinstance(e, dict):
        raise TypeError(f"effect must be a dict, got {type(e).__name__}")

    keep = ("type", "amount", "options", "faction", "optional", "target", "note")
    eff = {k: e[k] for k in keep if k in e}

    # If there are any extra keys beyond 'keep' and 'trigger', keep them too
    # so we won't lose future extensions (e.g., conditions).
    for k, v in e.items():
        if k not in keep and k != "trigger":
            eff[k] = v
    return eff


def _migrate_bucket(
    raw: Dict[str, Any], key: str, trigger: str, out_list: List[Dict[str, Any]]
):
    for e in raw.get(key) or []:
        eff = _copy_effect_fields(e)
        eff["trigger"] = trigger
        out_list.append(eff)


def _normalize_card(raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    Accept card dicts in either legacy (on_play/scrap/activated/ally/passive)
    or unified (effects) schema and return a normalized dict:
      {
        name, faction, type, cost, defense, outpost,
        effects: [{trigger,type,amount?,options?,faction?,optional?,target?,note?,...}]
      }
    """
    if not isinstance(raw, dict):
        raise TypeError(f"Card entry must be a dict, got {type(raw).__name__}")

    name = raw.get("name") or ""
    faction = raw.get("faction", "Neutral")
    ctype = raw.get("type", "ship")
    cost = _as_int(raw.get("cost", 0))
    defense = _as_int(raw.get("defense", 0))
    outpost = bool(raw.get("outpost", False))

    effects: List[Dict[str, Any]] = []

    # --- Legacy buckets -> unified effects (preserve amount/options/etc.)
    _migrate_bucket(raw, "on_play", "play", effects)
    _migrate_bucket(raw, "scrap", "scrap", effects)
    _migrate_bucket(raw, "activated", "activate", effects)
    _migrate_bucket(raw, "passive", "passive", effects)

    # Ally: default faction to the card's faction if not provided
    for e in raw.get("ally") or []:
        eff = _copy_effect_fields(e)
        eff["trigger"] = "ally"
        eff.setdefault("faction", faction)
        effects.append(eff)

    # --- Already-unified effects (keep trigger if present; default to 'play')
    for e in raw.get("effects") or []:
        eff = _copy_effect_fields(e)
        eff["trigger"] = e.get("trigger", "play")
        effects.append(eff)

    return {
        "name": name,
        "faction": faction,
        "type": ctype,
        "cost": cost,
        "defense": defense,
        "outpost": outpost,
        "effects": effects,
    }


def _validate_card(c: Dict[str, Any]) -> None:
    if not c.get("name"):
        raise ValueError("Card missing 'name'")
    if c.get("type") not in ("ship", "base"):
        raise ValueError(f"{c.get('name')}: invalid type {c.get('type')}")
    if c.get("cost", 0) < 0:
        raise ValueError(f"{c.get('name')}: negative cost")
    if c["type"] == "base" and _as_int(c.get("defense", 0)) <= 0:
        raise ValueError(f"{c.get('name')}: base must have positive defense")

    # Effects basic sanity
    allowed_triggers = {"play", "scrap", "activate", "ally", "on_acquire", "passive"}
    for e in c.get("effects", []):
        if "type" not in e:
            raise ValueError(f"{c.get('name')}: effect missing 'type'")
        trig = e.get("trigger")
        if trig is not None and trig not in allowed_triggers:
            raise ValueError(f"{c.get('name')}: invalid trigger {trig}")


# --- Module loading & building ------------------------------------------------


def _import_enabled_modules():
    errors = []
    mods = []
    for path in ENABLED_SETS:
        try:
            mods.append(import_module(f".{path}", __name__))
        except Exception as e:
            errors.append(f"Failed to import set '{path}': {e!r}")
    if errors:
        raise RuntimeError("Card set import errors:\n- " + "\n- ".join(errors))
    return mods


def _merge_cards_from_modules(mods) -> List[Dict[str, Any]]:
    merged: List[Dict[str, Any]] = []
    for m in mods:
        if not hasattr(m, "CARDS"):
            raise RuntimeError(f"Set module '{m.__name__}' is missing CARDS list")
        lst = getattr(m, "CARDS")
        for i, rc in enumerate(lst):
            try:
                c = _normalize_card(rc)
                _validate_card(c)
                merged.append(c)
            except Exception as e:
                raise RuntimeError(f"[{m.__name__}] CARDS[{i}] invalid: {e}") from e
    _assert_no_duplicate_names(merged)
    return merged


def _assert_no_duplicate_names(cards: List[Dict[str, Any]]):
    seen = set()
    dups = set()
    for c in cards:
        n = c["name"]
        if n in seen:
            dups.add(n)
        seen.add(n)
    if dups:
        raise RuntimeError("Duplicate card names detected: " + ", ".join(sorted(dups)))


def _load():
    global CARDS, _modules
    _modules = _import_enabled_modules()
    all_cards = _merge_cards_from_modules(_modules)
    CARDS[:] = all_cards
    _logger.debug("Loaded %d cards from %d sets", len(CARDS), len(_modules))


# --- Trade deck building (duplicates allowed, must be consistent) ------------


def _freeze(obj):
    """
    Recursively convert dicts/lists into hashable tuples for stable comparisons.
    - dict -> tuple(sorted((key, freeze(value)) ...))
    - list -> tuple(freeze(item) ...)
    - scalars -> as-is
    """
    if isinstance(obj, dict):
        return tuple(sorted((k, _freeze(v)) for k, v in obj.items()))
    if isinstance(obj, list):
        return tuple(_freeze(x) for x in obj)
    return obj


def _fingerprint(c: Dict[str, Any]) -> Tuple:
    """Minimal fingerprint to ensure copies of the same-named card are consistent."""
    return (
        c.get("name"),
        c.get("faction"),
        c.get("type"),
        int(c.get("cost", 0)),
        int(c.get("defense", 0)),
        bool(c.get("outpost", False)),
        tuple(
            (
                e.get("trigger", "play"),
                e.get("type"),
                int(e.get("amount", 0) if e.get("amount") is not None else 0),
                _freeze(e.get("options")) if "options" in e else None,
            )
            for e in c.get("effects", [])
        ),
    )


def build_trade_deck() -> List[Dict[str, Any]]:
    """
    Combined trade deck from all enabled sets.
    Each set module must define build_trade_deck() returning a list of card dict copies.
    All cards returned are normalized + validated here (so callers don’t have to).

    NOTE: Duplicate names are EXPECTED in the trade deck (multiple copies).
          We only ensure that copies with the same name are internally consistent.
    """
    if not _modules:
        _load()

    deck: List[Dict[str, Any]] = []
    errors: List[str] = []

    for m in _modules:
        fn = getattr(m, "build_trade_deck", None)
        if not callable(fn):
            errors.append(f"Set module '{m.__name__}' missing build_trade_deck()")
            continue
        try:
            raw_list = fn()
            for i, rc in enumerate(raw_list):
                try:
                    c = _normalize_card(rc)
                    _validate_card(c)
                    deck.append(c)
                except Exception as e:
                    errors.append(
                        f"[{m.__name__}] build_trade_deck()[{i}] invalid: {e}"
                    )
        except Exception as e:
            errors.append(f"[{m.__name__}] build_trade_deck() error: {e!r}")

    if errors:
        raise RuntimeError("Trade deck build errors:\n- " + "\n- ".join(errors))

    # Consistency guard: same-name copies should match on core fields/effects
    by_name: Dict[str, Tuple] = {}
    mismatches = []
    for c in deck:
        fp = _fingerprint(c)
        n = c["name"]
        if n not in by_name:
            by_name[n] = fp
        elif by_name[n] != fp:
            mismatches.append(n)

    if mismatches:
        uniq = ", ".join(sorted(set(mismatches)))
        raise RuntimeError(
            "Inconsistent duplicate card definitions for: "
            + uniq
            + " (cards with the same name have different fields/effects)"
        )

    # DO NOT call _assert_no_duplicate_names(deck) here — duplicates are valid in the trade deck
    return deck


def reload_enabled_sets(new_enabled: List[str] | None = None) -> int:
    """
    Optional helper for tests/dev: update ENABLED_SETS and reload.
    Returns number of loaded cards.
    """
    global ENABLED_SETS
    if new_enabled is not None:
        ENABLED_SETS = list(new_enabled)
    _load()
    return len(CARDS)


# Load at import time
_load()

# Build quick indexes and expose EXPLORER for tests/engine convenience
CARD_INDEX: Dict[str, Dict[str, Any]] = {c["name"]: c for c in CARDS}
try:
    EXPLORER = CARD_INDEX[EXPLORER_NAME]  # template (don’t mutate; copy before use)
except KeyError:
    EXPLORER = None  # if a set omits Explorer, tests can assert on this
