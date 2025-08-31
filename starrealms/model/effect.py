from dataclasses import dataclass, field
from typing import Optional, Dict, Any, Literal

Trigger = Literal["on_play", "ally", "scrap", "activated", "passive", "start_of_turn"]


@dataclass(frozen=True)
class EffectSpec:
    trigger: Trigger
    type: str
    amount: Optional[int] = None
    args: Dict[str, Any] = field(default_factory=dict)
