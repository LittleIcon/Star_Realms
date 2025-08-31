# at the top of runner/human.py (and any CLI module that reads input)
from starrealms.view.ui_common import ui_input, ui_print

from starrealms.engine.game import Game
from starrealms.view.render import print_state


def run(seed: int = 0):
    g = Game(seed=seed)
    while not g.is_over():
        print_state(g.state)
        break
    if g.winner():
        print("Winner:", g.winner())
