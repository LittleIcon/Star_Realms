# tests/test_resolver_unit.py
import importlib
import types

resolver = importlib.import_module("starrealms.engine.resolver")


class DummyPlayer:
    def __init__(self, name="P"):
        self.name = name
        self.hand = []
        self.in_play = []
        self.bases = []
        self.discard_pile = []
        self.scrap_heap = []
        self.deck = []
        self.authority = 50
        self.trade_pool = 0
        self.combat_pool = 0
        # flags the resolver may toggle:
        # ally_wildcard_active
        # topdeck_next_purchase

    def draw_card(self):
        if self.deck:
            c = self.deck.pop(0)
            self.hand.append(c)
            return c
        return None


class DummyGame:
    def __init__(self):
        self.log = []
        self.trade_row = []
        self.trade_deck = []
        self.scrap_heap = []


def test_can_handle_known_kinds():
    for kind in [
        "trade",
        "combat",
        "authority",
        "draw",
        "discard_then_draw",
        "opponent_discards",
        "scrap_hand_or_discard",
        "destroy_base",
        "destroy_target_trade_row",
        "ally_any_faction",
        "topdeck_next_purchase",
    ]:
        assert resolver.can_handle(kind), f"resolver cannot handle {kind}"


def test_apply_trade_combat_authority_and_log():
    g, p1, p2 = DummyGame(), DummyPlayer("P1"), DummyPlayer("P2")
    resolver.apply_effect(g, p1, p2, {"type": "trade", "amount": 3})
    resolver.apply_effect(g, p1, p2, {"type": "combat", "amount": 4})
    resolver.apply_effect(g, p1, p2, {"type": "authority", "amount": 5})
    assert p1.trade_pool == 3
    assert p1.combat_pool == 4
    assert p1.authority == 55
    assert any("gains +3 trade" in line for line in g.log)
    assert any("gains +4 combat" in line for line in g.log)
    assert any("gains 5 authority" in line for line in g.log)


def test_draw_and_discard_then_draw():
    g, p1, p2 = DummyGame(), DummyPlayer("P1"), DummyPlayer("P2")
    # prepare deck for draws
    p1.deck = [{"name": "A"}, {"name": "B"}, {"name": "C"}]
    resolver.apply_effect(g, p1, p2, {"type": "draw", "amount": 2})
    assert [c["name"] for c in p1.hand] == ["A", "B"]

    # now put some cards in hand, and more in deck to draw back
    p1.hand = [{"name": "H1"}, {"name": "H2"}, {"name": "H3"}]
    p1.deck = [{"name": "D1"}, {"name": "D2"}]
    start = len(p1.hand)
    resolver.apply_effect(g, p1, p2, {"type": "discard_then_draw", "amount": 2})
    # net hand size unchanged
    assert len(p1.hand) == start


def test_opponent_discards_moves_card():
    g, p1, p2 = DummyGame(), DummyPlayer("P1"), DummyPlayer("P2")
    p2.hand = [{"name": "Scout"}, {"name": "Viper"}]
    resolver.apply_effect(g, p1, p2, {"type": "opponent_discards", "amount": 1})
    assert len(p2.hand) == 1
    assert any(c["name"] in ("Scout", "Viper") for c in p2.discard_pile)


def test_scrap_hand_or_discard_by_zone_and_idx():
    g, p1, p2 = DummyGame(), DummyPlayer("P1"), DummyPlayer("P2")

    # scrap from hand, idx 1
    p1.hand = [{"name": "H0"}, {"name": "H1"}, {"name": "H2"}]
    resolver.apply_effect(g, p1, p2, {"type": "scrap_hand_or_discard", "args": {"zone": "hand", "idx": 1}})
    assert [c["name"] for c in p1.hand] == ["H0", "H2"]
    assert any(c["name"] == "H1" for c in p1.scrap_heap) or any(c["name"] == "H1" for c in g.scrap_heap)

    # scrap from discard, default idx 0
    p1.discard_pile = [{"name": "D0"}, {"name": "D1"}]
    resolver.apply_effect(g, p1, p2, {"type": "scrap_hand_or_discard", "args": {"zone": "discard"}})
    assert [c["name"] for c in p1.discard_pile] == ["D1"]


def test_destroy_base_prioritizes_outpost_and_scraps_it():
    g, p1, p2 = DummyGame(), DummyPlayer("P1"), DummyPlayer("P2")
    normal = {"name": "Base B", "type": "base", "defense": 5, "outpost": False}
    outpost = {"name": "Outpost A", "type": "base", "defense": 3, "outpost": True}
    p2.bases[:] = [normal, outpost]

    resolver.apply_effect(g, p1, p2, {"type": "destroy_base"})
    names = [b["name"] for b in p2.bases]
    assert "Outpost A" not in names
    assert "Base B" in names
    assert any(x.get("name") == "Outpost A" for x in g.scrap_heap)


def test_destroy_target_trade_row_removes_and_refills_from_deck():
    g, p1, p2 = DummyGame(), DummyPlayer("P1"), DummyPlayer("P2")
    t0 = {"name": "Cutter", "cost": 2}
    refill = {"name": "Refill", "cost": 3}
    g.trade_row = [t0]
    g.trade_deck = [refill]  # popped by resolver, inserted into same slot

    resolver.apply_effect(g, p1, p2, {"type": "destroy_target_trade_row", "args": {"idx": 0}})
    assert t0 not in g.trade_row
    assert g.trade_row and g.trade_row[0] is refill
    assert any(x.get("name") == "Cutter" for x in g.scrap_heap)


def test_ally_any_and_topdeck_flags():
    g, p1, p2 = DummyGame(), DummyPlayer("P1"), DummyPlayer("P2")
    assert not getattr(p1, "ally_wildcard_active", False)
    resolver.apply_effect(g, p1, p2, {"type": "ally_any_faction"})
    assert getattr(p1, "ally_wildcard_active", False)

    assert not getattr(p1, "topdeck_next_purchase", False)
    resolver.apply_effect(g, p1, p2, {"type": "topdeck_next_purchase"})
    assert getattr(p1, "topdeck_next_purchase", False)


def test_has_ally_true_when_wildcard_or_matching_faction_present():
    # NOTE: resolver.__all__ exports has_ally; per code, the **last** has_ally defined
    # takes (player, faction) and checks for wildcard flag or same-faction in play/bases.
    has_ally = getattr(resolver, "has_ally")
    g, p1, p2 = DummyGame(), DummyPlayer("P1"), DummyPlayer("P2")

    # 1) wildcard flag
    p1.ally_wildcard_active = True
    assert has_ally(p1, "Blob") is True
    delattr(p1, "ally_wildcard_active")

    # 2) same-faction present
    p1.in_play.append({"name": "Blob Fighter", "faction": "Blob"})
    assert has_ally(p1, "Blob") is True

    # 3) via Mech World inference
    p1.in_play.clear()
    p1.bases.append({"name": "Mech World", "type": "base", "outpost": True})
    assert has_ally(p1, "Star Empire") is True