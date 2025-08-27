# main.py
from starrealms import Player, Game, BASE_TEST_SET, play_all_cards, attack, buy_card

def human_turn(game, player, opponent):
    player.start_turn()
    while True:
        print("\n--- YOUR TURN ---")
        print(f"Your Authority: {player.authority} | Opponent: {opponent.name} ({opponent.authority})")
        print(f"Trade: {player.trade} | Combat: {player.combat}")
        print("Hand:", [c.name for c in player.hand])
        print("In Play:", [c.name for c in player.in_play])
        print("Trade Row:", [(c.name, c.cost) for c in game.trade_row])
        cmd = input("Command (play all / buy <card> / attack / end): ").strip().lower()
        if cmd == "play all":
            play_all_cards(player, opponent, game)
        elif cmd.startswith("buy "):
            buy_card(cmd[4:], player, game)
        elif cmd == "attack":
            attack(player, opponent)
        elif cmd == "end":
            player.end_turn()
            break
        else:
            print("Invalid command.")

def ai_turn(game, player, opponent):
    print(f"\n--- {player.name}'s TURN ---")
    player.start_turn()
    play_all_cards(player, opponent, game)
    attack(player, opponent)
    for c in list(game.trade_row):
        if c.cost <= player.trade:
            buy_card(c.name, player, game)
            break
    player.end_turn()

def play_game():
    players = [Player("You", human=True), Player("ChatGPT")]
    game = Game(players)
    game.start(BASE_TEST_SET)
    while all(p.authority > 0 for p in players):
        current = game.get_current_player()
        opponent = game.players[(game.current_player + 1) % 2]
        if current.human:
            human_turn(game, current, opponent)
        else:
            ai_turn(game, current, opponent)
        game.next_player()
        if opponent.authority <= 0:
            print(f"{current.name} wins!")
            break

if __name__ == "__main__":
    play_game()