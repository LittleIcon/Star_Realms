# starrealms/agent/human.py
from typing import Optional
from starrealms.view.ui_common import ui_print, ui_input

class HumanAgent:
    def __init__(self, name: str = "Human"):
        self.name = name

    def choose_index(self, prompt: str, n: int, cancellable: bool = True) -> Optional[int]:
        while True:
            raw = ui_input(prompt).strip().lower()
            if cancellable and raw in ("x", ""):
                return None
            if raw.isdigit():
                i = int(raw)
                if 1 <= i <= n:
                    return i
            ui_print("❗ Invalid choice.")

    def choose_pile(
        self, prompt: str, *, can_hand: bool, can_discard: bool, cancellable: bool = True
    ) -> Optional[str]:
        while True:
            raw = ui_input(prompt).strip().lower()
            if cancellable and raw in ("x", ""):
                return None
            if raw in ("h", "hand") and can_hand:
                return "h"
            if raw in ("d", "discard") and can_discard:
                return "d"
            ui_print("❗ Invalid choice.")

    def choose_option(self, prompt: str, n: int, cancellable: bool = True) -> Optional[int]:
        return self.choose_index(prompt, n, cancellable)