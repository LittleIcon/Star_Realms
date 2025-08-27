# main.py
import sys
from starrealms.game import Game
from starrealms.ai import PolicyAgent, GoodHeuristicAgent, load_weights, train
from starrealms.runner.human import human_turn
from starrealms.runner.ai_runner import ai_turn   # only if you split AI turn

def choose_mode():
    print("Select opponent type:")
    print("  1) Simple AI (baseline)")
    print("  2) Good AI (hard-coded heuristics)")
    print("  h) Human (hotseat)")
    while True:
        sel = input("Opponent? [1/2/h] > ").strip().lower()
        if sel == "1": return "ai_simple"
        if sel == "2": return "ai_good"
        if sel == "h": return "human"
        print("Please choose 1, 2, or h.")

def _mark_players(game, p1_human: bool, p2_human: bool) -> None:
    """Ensure players have .human set so UI prompts (scrap, choices, etc.) appear."""
    try:
        p1, p2 = game.players[0], game.players[1]
    except Exception:
        # Fallback for engines that expose differently
        p1, p2 = game.current_player(), game.opponent()
    setattr(p1, "human", p1_human)
    setattr(p2, "human", p2_human)

def play_mode():
    mode = choose_mode()
    if mode == "ai_simple":
        agent = PolicyAgent(load_weights())
        game = Game(("Player 1", "AI (Simple)"))
        _mark_players(game, p1_human=True, p2_human=False)
    elif mode == "ai_good":
        agent = GoodHeuristicAgent()
        game = Game(("Player 1", "AI (Good)"))
        _mark_players(game, p1_human=True, p2_human=False)
    else:
        agent = None
        game = Game(("Player 1", "Player 2"))
        _mark_players(game, p1_human=True, p2_human=True)  # hotseat

    last_log_len = 0
    while True:
        winner = game.check_winner()
        if winner:
            print(f"\n🎉 {winner.name} wins! 🎉")
            break

        if game.current_player().name == "Player 1":
            last_log_len = human_turn(game, last_log_len)
        else:
            last_log_len = ai_turn(game, agent, last_log_len) if agent else human_turn(game, last_log_len)

        winner = game.check_winner()
        if winner:
            print(f"\n🎉 {winner.name} wins! 🎉")
            break

def train_mode(iters: int):
    def make_game():
        g = Game(("A", "B"))
        _mark_players(g, p1_human=False, p2_human=False)
        return g
    print(f"Starting training for {iters} iterations...")
    best = train(make_game, iterations=iters, matches_per_iter=20, log_fn=print)
    print("Training complete. Current best weights:")
    for k, v in sorted(best.items()):
        print(f"  {k}: {v}")

if __name__ == "__main__":
    args = sys.argv[1:]
    if args and args[0] == "--train":
        iters = int(args[1]) if len(args) > 1 and args[1].isdigit() else 100
        train_mode(iters)
    else:
        play_mode()