from random import Random
from starrealms.engine.state import GameState, PlayerState
from starrealms.model.card import build_trade_deck


class Game:
    def __init__(self, p1="Player 1", p2="AI", seed: int = 0):
        deck = build_trade_deck()
        rng = Random(seed)
        rng.shuffle(deck)
        self.state = GameState(
            rng=rng,
            players={"P1": PlayerState(p1), "P2": PlayerState(p2)},
            trade_row=[deck.pop() for _ in range(5)],
            trade_deck=deck,
        )
        self.state.draw("P1", 3)
        self.state.draw("P2", 5)

    def is_over(self) -> bool:
        return any(p.authority <= 0 for p in self.state.players.values())

    def winner(self):
        if not self.is_over():
            return None
        return "P1" if self.state.players["P2"].authority <= 0 else "P2"
