# starrealms/view/ui_common.py
"""
Minimal UI shim used by engine/runner code.
- In CLI mode, ui_print -> print, ui_input -> input.
- In Pygame (or tests), you can monkey-patch ui_input / ui_print.
"""

from typing import Any, Iterable


def ui_print(*args: Any, **kwargs: Any) -> None:
    print(*args, **kwargs)


def ui_log(game, message: str) -> None:
    if getattr(game, "log", None) is not None:
        game.log.append(message)
    ui_print(message)


def ui_input(prompt: str = "") -> str:
    """Default CLI input. In Pygame, monkey-patch this function."""
    return input(prompt)


# Optional convenience used by CLI runners:
def ui_confirm(prompt: str = "Continue? [y/N] ") -> bool:
    return ui_input(prompt).strip().lower() in {"y", "yes"}


def ui_choose_index(
    n: int, prompt: str = "Choose index (1-based) or 'x': "
) -> int | None:
    """
    Returns 0-based index, or None if user types 'x' / empty.
    """
    s = ui_input(prompt).strip().lower()
    if s in {"x", ""}:
        return None
    try:
        k = int(s)
    except ValueError:
        return None
    if 1 <= k <= n:
        return k - 1
    return None


# Tiny tool for scripted input (handy for tests / Pygame headless)
class ScriptedInput:
    """
    Callable that returns pre-seeded responses, then a fallback (default 'x').
    Example:
        ui_input = ScriptedInput(["1", "x"])
    """

    def __init__(self, responses: Iterable[str], fallback: str = "x"):
        self._it = iter(responses)
        self._fallback = fallback

    def __call__(self, prompt: str = "") -> str:
        try:
            return next(self._it)
        except StopIteration:
            return self._fallback
