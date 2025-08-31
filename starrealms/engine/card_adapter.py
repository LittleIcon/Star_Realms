# engine/card_adapter.py
from __future__ import annotations
import json
from copy import deepcopy
from typing import Any, Dict, List


def _normalize_choose(effect: Dict[str, Any]) -> Dict[str, Any]:
    """
    Accepts legacy shapes like:
      { "type": "choose", "options": [[{...}], [{...}]] }
      { "type": "choose", "options": [{"type":"trade","amount":1}, {"effects":[...]}] }
    Returns:
      { "type": "choose_one", "options": [{"label": "...","effects":[...]}, ...] }
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


def _map_passive_to_continuous(
    effect: Dict[str, Any], card_name: str
) -> List[Dict[str, Any]]:
    """
    Map legacy 'passive' effects to continuous hooks.
    Currently handles combat_per_ship; passes others through for later support.
    """
    t = effect.get("type")
    if t == "combat_per_ship":
        amt = int(effect.get("amount", 1))
        return [
            {
                "trigger": "continuous:on_ship_played",
                "effects": [{"type": "combat", "amount": amt}],
                "id": f"{card_name}_cont_ship_play",
            }
        ]
    # Mech World style: treat any faction as ally — keep as continuous effect for engine to support
    if t == "ally_any_faction":
        return [
            {
                "trigger": "continuous:modify_ally_checks",
                "effects": [{"type": "ally_any_faction"}],
                "id": f"{card_name}_cont_ally_any",
            }
        ]
    # Fallback: wrap as an on_turn_start if it's a simple numeric buff (rare)
    return [
        {
            "trigger": "on_turn_start",
            "effects": [effect],
            "id": f"{card_name}_passive_as_turnstart",
        }
    ]


def _to_unified(card: Dict[str, Any]) -> Dict[str, Any]:
    c = deepcopy(card)
    abilities: List[Dict[str, Any]] = []

    name = c.get("name", f"id{c.get('id','?')}")

    # on_play -> trigger:on_play
    for eff in c.get("on_play", []) or []:
        if isinstance(eff, dict) and eff.get("type") == "choose":
            eff = _normalize_choose(eff)
        abilities.append(
            {
                "id": f"{name}_on_play_{len(abilities)}",
                "trigger": "on_play",
                "effects": [eff] if isinstance(eff, dict) else eff,
            }
        )

    # activated -> trigger:activated (once/turn)
    for eff in c.get("activated", []) or []:
        if isinstance(eff, dict) and eff.get("type") == "choose":
            eff = _normalize_choose(eff)
        abilities.append(
            {
                "id": f"{name}_activated_{len(abilities)}",
                "trigger": "activated",
                "frequency": {"once_per_turn": True},
                "effects": [eff] if isinstance(eff, dict) else eff,
            }
        )

    # ally -> trigger:on_play with condition:faction_in_play(this card's faction)
    faction = c.get("faction")
    for eff in c.get("ally", []) or []:
        if isinstance(eff, dict) and eff.get("type") == "choose":
            eff = _normalize_choose(eff)
        abilities.append(
            {
                "id": f"{name}_ally_{len(abilities)}",
                "trigger": "on_play",
                "condition": {
                    "faction_in_play": {
                        "faction": faction,
                        "min": 1,
                        "scope": "this_turn",
                    }
                },
                "effects": [eff] if isinstance(eff, dict) else eff,
            }
        )

    # passive -> continuous hooks (or turn-start)
    for eff in c.get("passive", []) or []:
        mapped = _map_passive_to_continuous(eff, name)
        abilities.extend(mapped)

    # scrap -> trigger:scrap_activated (player-initiated)
    if c.get("scrap"):
        effects = []
        for eff in c["scrap"]:
            effects.extend(eff if isinstance(eff, list) else [eff])
        abilities.append(
            {"id": f"{name}_scrap", "trigger": "scrap_activated", "effects": effects}
        )

    # Special legacy cases embedded inside activated:
    # e.g., {"type":"start_of_turn","effect":{...}} -> turn-start trigger
    for eff in c.get("activated", []) or []:
        if isinstance(eff, dict) and eff.get("type") == "start_of_turn":
            abilities.append(
                {
                    "id": f"{name}_turnstart_{len(abilities)}",
                    "trigger": "on_turn_start",
                    "effects": [eff["effect"]],
                }
            )

    # Build unified card
    unified = {
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
        "abilities": abilities,
    }
    return unified


def adapt_cards_legacy_to_unified(cards: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [_to_unified(card) for card in cards]


def adapt_file(in_path: str, out_path: str) -> None:
    with open(in_path, "r", encoding="utf-8") as f:
        cards = json.load(f)
    unified = adapt_cards_legacy_to_unified(cards)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(unified, f, indent=2, ensure_ascii=False)
    print(f"Wrote {len(unified)} cards to {out_path}")
