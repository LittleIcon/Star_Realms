# tests/test_agent_bridge_outpost_rule.py
from starrealms.game import Game
from starrealms.effects import apply_effect

class PickingAIAgent:
    def choose_base_to_destroy(self, bases):
        # Always try the first one (which we set up as a non-outpost) to test enforcement
        return 0
    # unused:
    def choose_pile_for_scrap(self, *a, **k): return None
    def choose_index(self, *a, **k): return None
    def choose_trade_row_to_destroy(self, *a, **k): return None
    def choose_cards_to_discard(self, *a, **k): return []
    def choose_ship_to_copy(self, *a, **k): return None

def test_destroy_base_enforces_outpost_first_and_notifies_dispatcher(monkeypatch):
    g = Game(("you","cpu"))
    p, o = g.current_player(), g.opponent()
    p.agent = PickingAIAgent()

    # Opponent has non-outpost first, outpost second
    normal = {"name": "Base B", "type": "base", "defense": 5, "outpost": False}
    outpost = {"name": "Outpost A", "type": "base", "defense": 3, "outpost": True}
    o.bases[:] = [normal, outpost]

    # Spy on dispatcher leave-play
    calls = []
    orig_leave = getattr(g.dispatcher, "on_card_leave_play", None)
    def spy_leave(owner_name, base_card):
        calls.append((owner_name, base_card.get("name")))
        if orig_leave: orig_leave(owner_name, base_card)
    g.dispatcher.on_card_leave_play = spy_leave

    # Try to destroy (agent will pick index 0 == non-outpost); should be rejected by rule.
    apply_effect({"type": "destroy_base"}, p, o, g)
    assert [b["name"] for b in o.bases] == ["Base B", "Outpost A"]
    assert calls == []

    # Now make agent pick the outpost by reordering list (or simulate pick=1)
    o.bases[:] = [outpost, normal]
    apply_effect({"type": "destroy_base"}, p, o, g)
    assert [b["name"] for b in o.bases] == ["Base B"]
    # Dispatcher notified once for the outpost removal
    assert any(n == o.name and card == "Outpost A" for (n, card) in calls)