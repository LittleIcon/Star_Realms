# pygame_log_main.py
"""
Run a game with prints suppressed and logs captured, no rendering.
Useful while wiring up pygame without dealing with a window yet.
"""

from starrealms.game import Game
from starrealms.runner.controller import apply_command
from starrealms.view import ui_common as ui  # the shim we made

# Monkey-patch: silence ui_print, keep ui_log writing to game.log
def _silent_print(*args, **kwargs):
    pass

def _log_only(game, msg: str):
    if getattr(game, "log", None) is not None:
        game.log.append(str(msg))

ui.ui_print = _silent_print
ui.ui_log = _log_only

def main():
    g = Game(("You", "AI"))
    last = 0
    g.start_turn()
    # Demo scripted turn so you can see logs being captured:
    # - play all, buy explorer, attack, end turn
    for cmd, arg in [("pa", None), ("b", "x"), ("a", None), ("e", None)]:
        last = apply_command(g, cmd, arg, last, echo=False)

    # Dump the captured log at the end so you can verify it worked
    print("\n=== Captured game.log ===")
    for line in g.log:
        print(line)

if __name__ == "__main__":
    main()