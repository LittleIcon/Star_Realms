from starrealms.effects import apply_effects

def test_draw_adds_cards_to_hand(game, p1, p2):
    # remember original count
    start = len(p1.hand)
    apply_effects({"type":"draw","amount":2}, p1, p2, game)
    assert len(p1.hand) == start + 2

def test_discard_then_draw_up_to(game, p1, p2):
    # ensure enough cards in hand (draw to at least 4)
    while len(p1.hand) < 4:
        p1.draw_card()
    start_hand = len(p1.hand)
    start_discard = len(p1.discard_pile)

    # engine should discard up to N, then draw same N
    apply_effects({"type":"discard_then_draw","amount":2}, p1, p2, game)

    # net hand size should be unchanged; discard increased by 2
    assert len(p1.hand) == start_hand
    assert len(p1.discard_pile) == start_discard + 2