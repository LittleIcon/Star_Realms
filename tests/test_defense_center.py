import pytest
from starrealms.game import Game

def get_card_by_name(cards, name):
    for c in cards:
        if c.get("name") == name:
            return c
    raise ValueError(f"Card {name} not found")

def test_defense_center_options_and_ally(monkeypatch):
    # Setup game
    g = Game(("P1", "P2"))
    p1 = g.current_player()
    p2 = g.opponent()

    # Give P1 the Defense Center base
    defense_center = get_card_by_name(g.trade_deck + g.card_db, "Defense Center")
    p1.bases.append(defense_center.copy())

    # --- Test Option 1: +3 Authority ---
    start_auth = p1.authority
    # Activate, choose "Authority +3"
    g.apply_effects([{
        "type": "choose_one",
        "options": [
            {"label": "Authority +3", "effects": [{"type": "authority", "amount": 3}]},
            {"label": "Combat +2",    "effects": [{"type": "combat",    "amount": 2}]}
        ]
    }], p1, p2, choice_index=0)
    assert p1.authority == start_auth + 3

    # --- Test Option 2: +2 Combat ---
    start_combat = p1.combat_pool
    g.apply_effects([{
        "type": "choose_one",
        "options": [
            {"label": "Authority +3", "effects": [{"type": "authority", "amount": 3}]},
            {"label": "Combat +2",    "effects": [{"type": "combat",    "amount": 2}]}
        ]
    }], p1, p2, choice_index=1)
    assert p1.combat_pool == start_combat + 2

    # --- Test Ally: +2 Combat ---
    # Simulate another Trade Federation card in play
    ally_card = get_card_by_name(g.trade_deck + g.card_db, "Federation Shuttle")
    p1.in_play.append(ally_card.copy())

    # Trigger the ally ability
    g.apply_effects([{"type": "combat", "amount": 2}], p1, p2)
    assert p1.combat_pool == start_combat + 4  # from Option 2 (2) + ally (2)