# tests/test_agent_bridge_discard_then_draw.py
from starrealms.game import Game
from starrealms.effects import apply_effect

class HumanishAgent:
    """Simulates a human: discards up to 2 by choosing indices, then stops."""
    def __init__(self, picks): self._picks = list(picks)
    def choose_cards_to_discard(self, hand, up_to_n):
        # Return exactly the planned indices (already 0-based) but clip to up_to_n
        return self._picks[:up_to_n]
    # unused here:
    def choose_pile_for_scrap(self, *a, **k): return None
    def choose_index(self, *a, **k): return None
    def choose_base_to_destroy(self, *a, **k): return None
    def choose_trade_row_to_destroy(self, *a, **k): return None
    def choose_ship_to_copy(self, *a, **k): return None

def test_discard_then_draw_uses_agent_choices():
    g = Game(("P1","P2"))
    p, o = g.current_player(), g.opponent()
    # Hand is H1,H2,H3; discard H2 and H3 (indices 1 and 2), draw 2
    p.hand[:] = [{"name":"H1"},{"name":"H2"},{"name":"H3"}]
    p.deck[:] = [{"name":"D1"},{"name":"D2"},{"name":"D3"}] + p.deck  # ensure draws available
    start_deck_len = len(p.deck)

    p.agent = HumanishAgent([1,2])
    apply_effect({"type":"discard_then_draw","amount":2}, p, o, g)

    # H2 and H3 moved to discard; drew 2
    assert [c["name"] for c in p.discard_pile[-2:]] == ["H2","H3"]
    assert len(p.deck) == start_deck_len - 2