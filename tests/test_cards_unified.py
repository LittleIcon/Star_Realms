import json
import os
import pytest

BASE_PATH = os.path.join(
    os.path.dirname(__file__),
    "..",
    "starrealms",
    "cards",
    "standalone",
    "base_set",
)

UNIFIED_FILE = os.path.join(BASE_PATH, "cards_unified.json")

@pytest.fixture(scope="session")
def unified_cards():
    with open(UNIFIED_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def test_all_cards_have_abilities(unified_cards):
    for card in unified_cards:
        assert "abilities" in card, f"{card['name']} missing abilities"
        assert isinstance(card["abilities"], list)

def test_no_legacy_fields(unified_cards):
    legacy_fields = ["on_play", "activated", "ally", "passive", "scrap"]
    for card in unified_cards:
        for lf in legacy_fields:
            assert lf not in card, f"{card['name']} still has legacy field {lf}"

def test_schema_version(unified_cards):
    for card in unified_cards:
        assert card.get("schema_version") == 2
