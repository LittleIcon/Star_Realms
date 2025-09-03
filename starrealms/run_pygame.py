# run_pygame.py
# Launch the Pygame UI with your existing engine.

from starrealms.graphics.pygame_view import StarRealmsPygameView

# Import your engine.
# Adjust these imports to your actual paths:
from starrealms.game import Game

def main():
    game = Game(("Player 1", "AI"))
    # If your Game needs setup like build_trade_deck() or start() call, do it here.

    ui = StarRealmsPygameView(game, w=1280, h=800)
    ui.loop()

if __name__ == "__main__":
    main()