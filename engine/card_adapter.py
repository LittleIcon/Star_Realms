# engine/card_adapter.py
from __future__ import annotations
import json
from copy import deepcopy
from typing import Any, Dict, List

def _normalize_choose(effect: Dict[str, Any]) -> Dict[str, Any]:
    """
    Legacy -> unified:
      {"type":"choose","options":[[...],[...]]} OR mixed forms
    => {"type":"choose_one","options":[{"label":"Option 1","effects":[...]}, ...]}
    """
    opts = effect.get("options", [])
    new_opts = []
    for i, opt in enumerate(opts, 1):
        if isinstance(opt, list):
            effs = opt
        elif isinstance(opt, dict):
            if "effects" in opt and isinstance(opt["effects"], list):
                effs = opt["effects"]
            elif "type" in opt:
                effs = [opt]
            else:
                effs = []
        else:
            effs = []
        new_opts.append({"label": f"Option {i}", "effects": effs})
    return {"type": "choose_one", "options": new_opts}

def _map_passive_to_continuous(effect: Dict[str, Any], card_name: str) -> List[Dict[str, Any]]:
    t = effect.get("type")
    if t == "combat_per_ship":
        amt = int(effect.get("amount", 1))
        return [{
            "trigger": "continuous:on_ship_played",
            "effects": [ {"type": "combat", "amount": amt} ],
            "id": f"{card_name}_cont_ship_play"
        }]
    if t == "ally_any_faction":
        return [{
            "trigger": "continuous:modify_ally_checks",
            "effects": [ {"type": "ally_any_faction"} ],
            "id": f"{card_name}_cont_ally_any"
        }]
    # Fallback: treat unknown passives as on_turn_start bumps
    return [{
        "trigger": "on_turn_start",
        "effects": [effect],
        "id": f"{card_name}_passive_as_turnstart"
    }]

def _wrap_effect(eff: Any) -> List[Dict[str, Any]]:
    # Make sure we always have a list of effect dicts
    if isinstance(eff, list):
        return eff
    elif isinstance(eff, dict):
        return [eff]
    else:
        return []

def _to_unified(card: Dict[str, Any]) -> Dict[str, Any]:
    c = deepcopy(card)
    abilities: List[Dict[str, Any]] = []
    name = c.get("name", f"id{c.get('id','?')}")
    faction = c.get("faction")

    # on_play -> trigger:on_play
    for eff in (c.get("on_play") or []):
        if isinstance(eff, dict) and eff.get("type") == "choose":
            eff = _normalize_choose(eff)
        abilities.append({
            "id": f"{name}_on_play_{len(abilities)}",
            "trigger": "on_play",
            "effects": _wrap_effect(eff)
        })

    # activated -> trigger:activated (once/turn)
    for eff in (c.get("activated") or []):
        if isinstance(eff, dict) and eff.get("type") == "choose":
            eff = _normalize_choose(eff)
        # special case legacy "start_of_turn"
        if isinstance(eff, dict) and eff.get("type") == "start_of_turn":
            abilities.append({
                "id": f"{name}_turnstart_{len(abilities)}",
                "trigger": "on_turn_start",
                "effects": _wrap_effect(eff.get("effect", {}))
            })
        else:
            abilities.append({
                "id": f"{name}_activated_{len(abilities)}",
                "trigger": "activated",
                "frequency": {"once_per_turn": True},
                "effects": _wrap_effect(eff)
            })

    # ally -> on_play + condition (faction_in_play this turn)
    for eff in (c.get("ally") or []):
        if isinstance(eff, dict) and eff.get("type") == "choose":
            eff = _normalize_choose(eff)
        abilities.append({
            "id": f"{name}_ally_{len(abilities)}",
            "trigger": "on_play",
            "condition": {"faction_in_play": {"faction": faction, "min": 1, "scope": "this_turn"}},
            "effects": _wrap_effect(eff)
        })

    # passive -> continuous hooks (or on_turn_start fallback)
    for eff in (c.get("passive") or []):
        abilities.extend(_map_passive_to_continuous(eff, name))

    # scrap -> scrap_activated
    if c.get("scrap"):
        effs: List[Dict[str, Any]] = []
        for eff in c["scrap"]:
            effs.extend(_wrap_effect(eff))
        abilities.append({
            "id": f"{name}_scrap",
            "trigger": "scrap_activated",
            "effects": effs
        })

    return {
        "schema_version": 2,
        "id": c.get("id"),
        "name": name,
        "faction": faction,
        "type": c.get("type"),
        "cost": c.get("cost"),
        "defense": c.get("defense"),
        "outpost": c.get("outpost", False),
        "set": c.get("set", "base"),
        "rules_version": "base-1.0",
        "abilities": abilities
    }

def adapt_cards_legacy_to_unified(cards: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [_to_unified(card) for card in cards]

def adapt_file(in_path: str, out_path: str) -> None:
    with open(in_path, "r", encoding="utf-8") as f:
        cards = json.load(f)
    unified = adapt_cards_legacy_to_unified(cards)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(unified, f, indent=2, ensure_ascii=False)
    print(f"Wrote {len(unified)} cards to {out_path}")
