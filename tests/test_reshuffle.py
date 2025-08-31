def test_draw_reshuffles_discard_into_deck(game, p1):
    # Tiny predictable deck (3) and discard (5)
    p1.deck = [{"name": f"C{i}", "type": "ship", "on_play": []} for i in range(3)]
    p1.discard_pile = [{"name": f"D{i}", "type": "ship", "on_play": []} for i in range(5)]
    p1.hand.clear()

    p1.draw_cards(4)

    assert len(p1.hand) == 4
    # deck was 3 -> 0, reshuffle brings 5 to deck, then 1 drawn -> deck 4 left
    assert len(p1.deck) == 4
    # All discard used by reshuffle
    assert len(p1.discard_pile) == 0

def test_draw_handles_empty_deck_and_discard(game, p1):
    p1.deck = []
    p1.discard_pile = []
    p1.hand.clear()

    got = p1.draw_card()
    assert got is None
    assert len(p1.hand) == 0
    assert len(p1.deck) == 0
    assert len(p1.discard_pile) == 0
