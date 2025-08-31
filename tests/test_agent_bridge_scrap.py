# tests/test_agent_bridge_scrap.py
from starrealms.game import Game
from starrealms.effects import apply_effect

class ForcingAIAgent:
    """Deterministic AI: prefers discard, never cancels mandatory."""
    def choose_pile_for_scrap(self, hand_len, discard_len, allow_cancel):  # noqa: D401
        return "discard" if discard_len else ("hand" if hand_len else None)
    def choose_index(self, prompt, max_len, allow_cancel=True):
        return 0 if max_len > 0 else None

    # unused in this file:
    def choose_base_to_destroy(self, bases): return 0 if bases else None
    def choose_trade_row_to_destroy(self, row): return 0 if row else None
    def choose_cards_to_discard(self, hand, up_to_n): return []
    def choose_ship_to_copy(self, eligible): return 0 if eligible else None

def test_scrap_hand_or_discard_AI_mandatory_uses_discard_first():
    g = Game(("P1","P2"))
    p, o = g.current_player(), g.opponent()
    p.agent = ForcingAIAgent()

    p.discard_pile[:] = [{"name": "D1"}, {"name": "D2"}]
    p.hand[:] = [{"name": "H1"}]

    apply_effect({"type": "scrap_hand_or_discard"}, p, o, g)

    # Should have moved D1 to scrap (not H1), and only one card scrapped.
    names = [c["name"] for c in g.scrap_heap]
    assert names[:1] == ["D1"]