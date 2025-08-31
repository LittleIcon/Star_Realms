from starrealms.effects import apply_effects

class DummyAgent:
    def choose_card(self, items, prompt=None):
        return items[0] if items else None
    def choose_index(self, indices, prompt=None):
        return 0

def test_destroy_base_respects_outpost(game, p1, p2):
    p1.agent = DummyAgent()

    normal = {"name": "Base B", "type": "base", "defense": 5, "outpost": False}
    outpost = {"name": "Outpost A", "type": "base", "defense": 3, "outpost": True}
    p2.bases[:] = [normal, outpost]

    eff = {"type": "destroy_base"}
    apply_effects(eff, p1, p2, game)

    # Outpost should be gone, normal base should still be around
    names = [c["name"] for c in p2.bases]
    assert "Outpost A" not in names
    assert "Base B" in names