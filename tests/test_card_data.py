# tests/test_card_data.py
from __future__ import annotations
import importlib
import json
from importlib import resources
from typing import Dict, Any, List, Tuple
import pytest

# -------------------------------------------------------------------
# Locate the JSON dataset via package resources (no hardcoded paths)
# -------------------------------------------------------------------
BASE_PKG = "starrealms.cards.standalone.base_set"
try:
    CARDS_JSON_PATH = resources.files(BASE_PKG) / "cards.json"
    COUNTS_JSON_PATH = resources.files(BASE_PKG) / "counts.json"
    DATASET_OK = CARDS_JSON_PATH.is_file() and COUNTS_JSON_PATH.is_file()
except Exception:
    DATASET_OK = False

# -------------------------------------------------------------------
# Import the card source:
# Prefer your new loader (starrealms.cards), else fall back to model.card
# -------------------------------------------------------------------
def _import_card_source():
    for mod in ("starrealms.cards", "model.card"):
        try:
            return importlib.import_module(mod)
        except ModuleNotFoundError:
            continue
    raise AssertionError("Could not import starrealms.cards or model.card")

cards_mod = _import_card_source()
EXPLORER_NAME = getattr(cards_mod, "EXPLORER_NAME", "Explorer")

# Factions enforced in your JSON (adjust if you expand)
KNOWN_FACTIONS = {"Neutral", "Blob", "Star Empire", "Machine Cult", "Trade Federation"}

# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------
def _iter_effects(card: Dict[str, Any]):
    """Yield all effect dicts from legacy-style buckets (tolerant)."""
    for key in ("on_play", "activated", "passive", "ally", "scrap"):
        for eff in card.get(key, []) or []:
            yield key, eff

def _assert_effect_dict(eff: Dict[str, Any], card_name: str):
    assert isinstance(eff, dict), f"{card_name}: effect should be dict, got {type(eff)}"
    et = eff.get("type")
    assert isinstance(et, str) and et.strip(), f"{card_name}: effect missing 'type'"
    # integer-ish fields should be ints if present
    for k in ("amount", "draw", "count", "defense", "min_allies", "require_bases"):
        if k in eff and eff[k] is not None:
            assert isinstance(eff[k], int), f"{card_name}: '{k}' should be int"

def _load_json_dataset() -> Tuple[List[Dict[str, Any]], Dict[str, Any] | List[Dict[str, Any]]]:
    with resources.as_file(CARDS_JSON_PATH) as p_cards, resources.as_file(COUNTS_JSON_PATH) as p_counts:
        with p_cards.open("r", encoding="utf-8") as f:
            all_cards = json.load(f)
        with p_counts.open("r", encoding="utf-8") as f:
            counts = json.load(f)
    return all_cards, counts

# -------------------------------------------------------------------
# Stub/engine-level expectations (Explorer + trade deck copies)
# -------------------------------------------------------------------
def test_explorer_template_exists_and_costs_two():
    explorer = getattr(cards_mod, "EXPLORER", None)
    assert isinstance(explorer, dict), "EXPLORER dict must exist (loader should expose it)"
    assert explorer.get("name") == EXPLORER_NAME
    assert explorer.get("type") == "ship"
    assert explorer.get("cost") == 2
    for _, eff in _iter_effects(explorer):
        _assert_effect_dict(eff, explorer["name"])

def test_build_trade_deck_returns_copies():
    assert hasattr(cards_mod, "build_trade_deck")
    deck = cards_mod.build_trade_deck()
    assert isinstance(deck, list) and len(deck) > 0
    if len(deck) >= 2:
        assert deck[0] is not deck[1], "Deck entries must be distinct dict copies"
    # Mutating a deck entry must not mutate the EXPLORER template
    name_before = getattr(cards_mod, "EXPLORER")["name"]
    deck[0]["name"] = name_before + " (mutated)"
    assert getattr(cards_mod, "EXPLORER")["name"] == name_before

# -------------------------------------------------------------------
# Full JSON dataset checks (auto-skip if dataset is not importable)
# -------------------------------------------------------------------
json_dataset = pytest.mark.skipif(
    not DATASET_OK, reason="cards.json / counts.json not found; JSON dataset checks skipped"
)

@json_dataset
def test_json_card_names_unique_nonempty():
    ALL_CARDS_JSON, _ = _load_json_dataset()
    names = [c.get("name") for c in ALL_CARDS_JSON]
    assert all(isinstance(n, str) and n.strip() for n in names), "Each card needs a non-empty name"
    assert len(names) == len(set(names)), "Card names must be unique"

@json_dataset
def test_json_card_shapes_and_factions():
    ALL_CARDS_JSON, _ = _load_json_dataset()
    valid_types = {"ship", "base"}  # in JSON, outpost is a flag on base
    for c in ALL_CARDS_JSON:
        assert isinstance(c, dict)
        assert isinstance(c.get("name"), str) and c["name"].strip()
        t = c.get("type")
        assert t in valid_types, f"Bad 'type': {t} on {c.get('name')}"
        assert isinstance(c.get("cost"), int) and c["cost"] >= 0
        f = c.get("faction")
        assert isinstance(f, str) and f.strip()
        assert f in KNOWN_FACTIONS, f"Unknown faction '{f}' on {c['name']}"
        if t == "base":
            assert isinstance(c.get("defense"), int) and c["defense"] > 0
            if "outpost" in c:
                assert isinstance(c["outpost"], bool)

@json_dataset
def test_json_effect_shapes():
    ALL_CARDS_JSON, _ = _load_json_dataset()
    for c in ALL_CARDS_JSON:
        for _, eff in _iter_effects(c):
            _assert_effect_dict(eff, c["name"])

@json_dataset
def test_json_has_explorer_and_it_matches_stub_expectations():
    ALL_CARDS_JSON, _ = _load_json_dataset()
    names = {c["name"]: c for c in ALL_CARDS_JSON}
    assert EXPLORER_NAME in names, f"Explorer '{EXPLORER_NAME}' missing from JSON"
    ex = names[EXPLORER_NAME]
    assert ex["type"] == "ship" and ex["cost"] == 2
    plays = [e for e in ex.get("on_play", []) if e.get("type") == "trade"]
    assert any(e.get("amount") == 2 for e in plays), "Explorer on_play should include trade +2"
    scraps = [e for e in ex.get("scrap", []) if e.get("type") == "combat"]
    assert any(e.get("amount") == 2 for e in scraps), "Explorer scrap should include combat +2"

@json_dataset
def test_counts_total_is_positive():
    _, COUNTS_JSON = _load_json_dataset()
    total = 0
    if isinstance(COUNTS_JSON, dict):
        total = sum(int(v) for v in COUNTS_JSON.values())
    elif isinstance(COUNTS_JSON, list):
        for row in COUNTS_JSON:
            total += int(row.get("count", 0))
    else:
        pytest.fail("counts.json must be dict or list")
    assert total > 0, "counts.json should sum to a positive deck size"