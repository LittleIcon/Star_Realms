from dataclasses import dataclass
from typing import Literal, Union
@dataclass(frozen=True) class PlayCard: index: int
@dataclass(frozen=True) class BuyCard: trade_row_index: int
@dataclass(frozen=True) class Attack: target: Literal["opponent","base"]; amount: int
@dataclass(frozen=True) class ScrapFromHand: index: int
Action = Union[PlayCard, BuyCard, Attack, ScrapFromHand]
