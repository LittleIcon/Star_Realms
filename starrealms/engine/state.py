from dataclasses import dataclass, field
from typing import List, Dict
from random import Random


@dataclass
class PlayerState:
    name: str
    authority: int = 50
    trade: int = 0
    combat: int = 0
    deck: list = field(default_factory=list)
    discard: list = field(default_factory=list)
    hand: list = field(default_factory=list)
    in_play: list = field(default_factory=list)
    bases: list = field(default_factory=list)


@dataclass
class GameState:
    rng: Random
    players: Dict[str, PlayerState]
    trade_row: list
    trade_deck: list
    scrap_heap: list = field(default_factory=list)
    log: list = field(default_factory=list)

    def player(self, pid: str) -> PlayerState:
        return self.players[pid]

    def opponent_of(self, pid: str) -> str:
        return next(k for k in self.players if k != pid)

    def draw(self, pid: str, n: int = 1) -> None:
        p = self.players[pid]
        for _ in range(n):
            if not p.deck:
                p.deck, p.discard = p.discard, []
                self.rng.shuffle(p.deck)
            if p.deck:
                p.hand.append(p.deck.pop())
