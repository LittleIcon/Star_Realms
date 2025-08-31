# tests/test_quick_coverage_wins.py

import random
from starrealms.game import Game
from starrealms.effects import apply_effect

def _ship(name, faction="Neutral"):
    return {"name": name, "type": "ship", "faction": faction, "on_play": []}

def _base(name, effects):
    # convenience: make a base with given activated effects list
    return {"name": name, "type": "base", "faction": "Neutral", "defense": 3, "outpost": False, "activated": effects}

def test_start_of_turn_effect_fires_only_for_owner():
    # P1 is current, P2 is opponent
    g = Game(("P1", "P2"))
    p1, p2 = g.current_player(), g.opponent()

    # Give P2 a base that adds +2 trade at start of THEIR turn
    base = _base("Trade Pinger", [{"type": "start_of_turn", "effect": {"type": "trade", "amount": 2}}])
    p2.bases.append(base)

    # Start P1's turn (no benefit to P2)
    g.start_turn()
    assert p2.trade_pool == 0

    # End P1; start P2 — now P2 should get +2 trade
    g.end_turn()
    g.start_turn()
    assert p2.trade_pool >= 2

def test_ally_effects_trigger_once_for_both_cards_when_second_enters():
    g = Game(("P1", "P2"))
    p, o = g.current_player(), g.opponent()

    # Two Star Empire ships with ally +2 combat
    a = {"name":"A","type":"ship","faction":"Star Empire","on_play":[], "ally":[{"type":"combat","amount":2}]}
    b = {"name":"B","type":"ship","faction":"Star Empire","on_play":[], "ally":[{"type":"combat","amount":2}]}

    p.hand[:] = [a, b]
    p.play_card(a, o, g)          # first: no ally yet
    assert p.combat_pool == 0

    p.play_card(b, o, g)          # second enters; engine re-checks allies for all in play
    # Both A and B allies should have fired exactly once → +4 total
    assert p.combat_pool == 4

def test_per_ship_combat_bonus_applies_to_new_ships():
    g = Game(("P1","P2"))
    p, o = g.current_player(), g.opponent()

    # Grant an aura: +1 combat per ship this turn
    apply_effect({"type": "per_ship_combat", "amount": 1}, p, o, g)

    # Play two ships; dispatcher should award +1 each time a ship enters play
    s1 = _ship("S1")
    s2 = _ship("S2")
    p.hand[:] = [s1, s2]

    p.play_card(s1, o, g)
    p.play_card(s2, o, g)

    assert p.combat_pool >= 2  # allow >= in case other effects add combat too

def test_choose_uses_first_option_and_applies_nested_list():
    g = Game(("P1","P2"))
    p, o = g.current_player(), g.opponent()

    # 'choose' always picks first option in our engine; first is a list of two effects
    eff = {
        "type": "choose",
        "options": [
            [ {"type":"trade","amount":2}, {"type":"draw","amount":1} ],
            [ {"type":"combat","amount":3} ]
        ]
    }
    hand_before = len(p.hand)
    apply_effect(eff, p, o, g)
    assert p.trade_pool >= 2
    assert len(p.hand) == hand_before + 1

def test_destroy_base_ai_path_prioritizes_outpost():
    g = Game(("AI1","AI2"))  # neither human
    p, o = g.current_player(), g.opponent()

    outpost = {"name": "Outpost A", "type": "base", "defense": 3, "outpost": True}
    normal  = {"name": "Base B",   "type": "base", "defense": 5, "outpost": False}
    o.bases[:] = [outpost, normal]

    # AI path (no prompts) should destroy an outpost first if one exists
    apply_effect({"type": "destroy_base"}, p, o, g)
    assert len(o.bases) == 1 and o.bases[0]["name"] == "Base B"

def test_destroy_trade_row_random_ai_path_scraps_one_and_refills(monkeypatch):
    g = Game(("AI1","AI2"))
    p, o = g.current_player(), g.opponent()

    # Make random deterministic so test is stable
    monkeypatch.setattr(random, "choice", lambda seq: seq[0])

    assert len(g.trade_row) == 5
    scrap_before = len(g.scrap_heap)

    apply_effect({"type": "destroy_target_trade_row"}, p, o, g)

    # Still 5 slots, and one card moved to scrap heap
    assert len(g.trade_row) == 5
    assert len(g.scrap_heap) == scrap_before + 1