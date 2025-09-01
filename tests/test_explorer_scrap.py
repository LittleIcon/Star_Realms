# tests/test_explorer_scrap.py
import pytest
from starrealms.game import Game
from starrealms.cards import get_card_by_name

def test_explorer_scrap_gives_2_combat_and_is_removed():
    g = Game(("P1", "P2"))
    p1, p2 = g.current_player(), g.opponent()

    # Give P1 an Explorer and play it
    explorer = get_card_by_name(g.trade_deck + g.card_db, "Explorer").copy()
    p1.hand.append(explorer)
    assert p1.play_card(explorer, p2, g) is True

    # Scrap-activate the Explorer
    before = p1.combat_pool
    assert p1.activate_ship(explorer, p2, g, scrap=True) is True

    # +2 combat from the Explorer scrap
    assert p1.combat_pool == before + 2

    # The Explorer should no longer be in play
    assert all(c.get("name") != "Explorer" for c in p1.in_play)

    # It should be in a scrap heap (engine may use game.scrap_heap or player.scrap_heap)
    game_heap = getattr(g, "scrap_heap", [])
    player_heap = getattr(p1, "scrap_heap", [])
    assert any(c.get("name") == "Explorer" for c in game_heap + player_heap)