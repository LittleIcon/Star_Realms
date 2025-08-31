# tests/test_effects_basic_unit.py

import copy
import types
from starrealms.game import Game
from starrealms.effects import apply_effect

def setup_game_nonhuman_actor():
    """
    Return (g, p, o) where p is NON-human actor (Player 2 by default)
    and o is opponent (Player 1).
    """
    g = Game(("Player 1", "Player 2"))
    p = g.players[1]  # Player 2 is non-human by default per your Game()
    o = g.players[0]
    return g, p, o

def test_trade_combat_authority_and_draw():
    g, p, o = setup_game_nonhuman_actor()
    start_trade, start_combat, start_auth = p.trade_pool, p.combat_pool, p.authority
    hand_sz = len(p.hand)
    # trade
    apply_effect({"type": "trade", "amount": 3}, p, o, g)
    # combat
    apply_effect({"type": "combat", "amount": 2}, p, o, g)
    # authority
    apply_effect({"type": "authority", "amount": 4}, p, o, g)
    # draw
    apply_effect({"type": "draw", "amount": 2}, p, o, g)

    assert p.trade_pool == start_trade + 3
    assert p.combat_pool == start_combat + 2
    assert p.authority == start_auth + 4
    assert len(p.hand) == hand_sz + 2

def test_topdeck_flag_and_choose_container():
    g, p, o = setup_game_nonhuman_actor()
    # choose auto-picks first option
    apply_effect({"type": "choose", "options": [[{"type": "trade", "amount": 1}]]}, p, o, g)
    assert p.trade_pool >= 1
    # topdeck flag
    apply_effect({"type": "topdeck_next_purchase"}, p, o, g)
    assert p.topdeck_next_purchase is True

def test_opponent_forced_discards_nonhuman_path():
    g, p, o = setup_game_nonhuman_actor()
    # Give opponent 2 dummy cards in hand
    o.hand[:] = [{"name": "Dummy A"}, {"name": "Dummy B"}]
    apply_effect({"type": "opponent_discards", "amount": 2}, p, o, g)
    assert len(o.hand) == 0
    assert len(o.discard_pile) == 2

def test_scrap_hand_or_discard_prefers_discard_then_hand_for_ai():
    g, p, o = setup_game_nonhuman_actor()
    p.discard_pile[:] = [{"name": "ScrapMe1"}, {"name": "ScrapMe2"}]
    p.hand[:] = [{"name": "HandCard"}]
    apply_effect({"type": "scrap_hand_or_discard"}, p, o, g)
    # AI path scraps from discard first
    assert any(c["name"] == "ScrapMe1" for c in p.scrap_heap)

def test_discard_then_draw_ai_path_discards_and_refills():
    g, p, o = setup_game_nonhuman_actor()
    # Prepare hand and deck so draws are deterministic
    p.hand[:] = [{"name": "H1"}, {"name": "H2"}]
    p.discard_pile[:] = []
    p.deck[:] = [{"name": "N1"}, {"name": "N2"}, {"name": "N3"}]
    start_deck_len = len(p.deck)
    apply_effect({"type": "discard_then_draw", "amount": 2}, p, o, g)
    # Discard 2 then draw 2 → hand size should be unchanged (2)
    assert len(p.hand) == 2
    assert len(p.deck) == start_deck_len - 2
    assert len(p.discard_pile) == 2  # the original two went to discard

def test_scrap_multiple_ai_path():
    g, p, o = setup_game_nonhuman_actor()
    p.discard_pile[:] = [{"name": "D1"}, {"name": "D2"}]
    p.hand[:] = [{"name": "H1"}]
    apply_effect({"type": "scrap_multiple", "amount": 2}, p, o, g)
    # Two total scrapped between discard+hand
    assert len(p.scrap_heap) >= 2

def test_destroy_base_auto_path():
    g, p, o = setup_game_nonhuman_actor()
    # Put a base on opponent (Player 1)
    base = {"name": "Opp Base", "type": "base", "defense": 4, "outpost": False}
    o.bases.append(base)
    apply_effect({"type": "destroy_base"}, p, o, g)
    assert len(o.bases) == 0  # destroyed
    # (Dispatcher notification happens inside; we just validate the removal path)

def test_destroy_trade_row_auto_path_refills_and_scraps():
    g, p, o = setup_game_nonhuman_actor()
    # Ensure trade row has items
    assert any(g.trade_row), "Trade row should start with cards"
    row_len_before = len(g.trade_row)
    apply_effect({"type": "destroy_target_trade_row"}, p, o, g)
    # Row should still have same number of slots after refill
    assert len(g.trade_row) == row_len_before
    # Card should be moved to game.scrap_heap
    assert len(g.scrap_heap) >= 1

def test_ally_any_faction_and_per_ship_combat_flags():
    g, p, o = setup_game_nonhuman_actor()
    assert not hasattr(p, "ally_wildcard_active")
    apply_effect({"type": "ally_any_faction"}, p, o, g)
    assert getattr(p, "ally_wildcard_active", False) is True
    # per_ship_combat bonus accumulates
    apply_effect({"type": "per_ship_combat", "amount": 1}, p, o, g)
    apply_effect({"type": "per_ship_combat", "amount": 2}, p, o, g)
    assert p.per_ship_combat_bonus == 3

def test_copy_target_ship_applies_target_on_play_effects():
    g, p, o = setup_game_nonhuman_actor()
    # Put TWO ships in play: one will be source (last played), one eligible to copy
    target_ship = {"name": "Target Ship", "type": "ship", "on_play": [{"type": "combat", "amount": 2}]}
    other_ship  = {"name": "Other Ship",  "type": "ship", "on_play": [{"type": "trade",  "amount": 1}]}
    # Arrange so 'source' = last in in_play; eligible excludes source
    p.in_play[:] = [target_ship, other_ship]
    start_combat, start_trade = p.combat_pool, p.trade_pool
    apply_effect({"type": "copy_target_ship"}, p, o, g)
    # Non-human path auto-picks last eligible (target_ship)
    # Copying target_ship's on_play should add +2 combat
    assert p.combat_pool == start_combat + 2
    # and no change to trade from this copy path
    assert p.trade_pool == start_trade