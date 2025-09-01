from starrealms.game import Game
from starrealms.cards import get_card_by_name

def test_battle_station_scraps_when_used():
    g = Game(("P1", "P2"))
    p1, p2 = g.current_player(), g.opponent()

    # Give P1 a Battle Station base (has only a scrap_activated ability: +5 combat)
    bs = get_card_by_name(g.trade_deck + g.card_db, "Battle Station").copy()
    p1.bases.append(bs)

    start_combat = p1.combat_pool
    # Activate the base (your engine should route scrap_activated correctly)
    assert p1.activate_base(bs, p2, g) is True

    # Combat increased by 5
    assert p1.combat_pool == start_combat + 5

    # The base should be removed from play
    assert all(b.get("name") != "Battle Station" for b in p1.bases)

    # And it should end up in the game's scrap heap (or player’s, depending on your engine’s convention)
    heap = getattr(g, "scrap_heap", []) or getattr(p1, "scrap_heap", [])
    assert any(c.get("name") == "Battle Station" for c in heap)

    # Optional: nice log line
    log = getattr(g, "log", [])
    assert any("scrap" in line.lower() and "Battle Station" in line for line in log)