# starrealms/agent/__init__.py
from typing import Optional, Protocol

class Agent(Protocol):
    name: str

    def choose_index(self, prompt: str, n: int, cancellable: bool = True) -> Optional[int]:
        ...

    def choose_pile(
        self, prompt: str, *, can_hand: bool, can_discard: bool, cancellable: bool = True
    ) -> Optional[str]:
        ...

    def choose_option(self, prompt: str, n: int, cancellable: bool = True) -> Optional[int]:
        ...