# tests/test_stealth_needle_copy_simple.py
import types
import pytest

from starrealms.effects import apply_effects

class _DummyPlayer:
    def __init__(self, name):
        self.name = name
        self.trade_pool = 0
        self.combat_pool = 0
        self.authority = 50
        self.hand = []
        self.discard_pile = []
        self.deck = []
        self.in_play = []
        self.bases = []
        self.agent = None
        self.human = False
        # some tests/paths look for these
        self.scrap_heap = []
        self.topdeck_next_purchase = False

    # effects engine may call draw in other paths; keep it harmless here
    def draw_card(self):
        if self.deck:
            self.hand.append(self.deck.pop(0))

class _DummyGame:
    def __init__(self):
        self.log = []
        self.trade_row = []
        self.trade_deck = []
        self.scrap_heap = []
        self.dispatcher = types.SimpleNamespace(
            on_card_leave_play=lambda *a, **k: None
        )

def test_stealth_needle_copies_explorer_on_play_for_trade():
    """
    When Stealth Needle copies Explorer, Explorer's on_play (+2 trade) should be applied.
    """
    game = _DummyGame()
    p1 = _DummyPlayer("P1")
    p2 = _DummyPlayer("P2")

    # Target ship to copy: Explorer with a simple on_play +2 trade.
    explorer = {
        "name": "Explorer",
        # For effects.py's _collect_on_play_effects, use the 'on_play' list shape.
        "on_play": [
            {"type": "trade", "amount": 2}
        ],
    }

    # The copier (Stealth Needle). We just need it to be the *last* card in in_play
    # so the copy effect can't target itself (effects.py excludes the last card).
    stealth_needle = {"name": "Stealth Needle"}

    # Seed board: Explorer already in play, then play Stealth Needle.
    p1.in_play = [explorer, stealth_needle]

    # Fire the effect that Stealth Needle's card JSON would trigger on play.
    apply_effects({"type": "copy_target_ship"}, p1, p2, game)

    # Expect Explorer's on_play to have run once: +2 trade.
    assert p1.trade_pool == 2

    # Nice-to-have: log line (effects.py adds this)
    assert any("Stealth Needle copies Explorer" in line for line in getattr(game, "log", []))