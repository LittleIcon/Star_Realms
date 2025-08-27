# starrealms.py
import random
from collections import deque

# ---------------------------
# Card class
# ---------------------------
class Card:
    def __init__(self, name, faction, cost, ctype,
                 effects=None, ally_effects=None, scrap_effects=None,
                 defense=0, outpost=False):
        self.name = name
        self.faction = faction
        self.cost = cost
        self.type = ctype  # 'ship' or 'base'
        self.effects = effects or []
        self.ally_effects = ally_effects or []
        self.scrap_effects = scrap_effects or []
        self.defense = defense
        self.outpost = outpost

    def __repr__(self):
        return f"{self.name}"

# ---------------------------
# Player
# ---------------------------
class Player:
    def __init__(self, name, human=False):
        self.name = name
        self.human = human
        self.authority = 50
        self.deck = deque()
        self.discard_pile = []
        self.hand = []
        self.in_play = []
        self.trade = 0
        self.combat = 0

    def draw(self, n=1):
        for _ in range(n):
            if not self.deck and self.discard_pile:
                random.shuffle(self.discard_pile)
                self.deck = deque(self.discard_pile)
                self.discard_pile = []
            if self.deck:
                self.hand.append(self.deck.popleft())

    def start_turn(self):
        self.trade = 0
        self.combat = 0

    def end_turn(self):
        for c in list(self.in_play):
            if c.type == "ship":
                self.discard_pile.append(c)
                self.in_play.remove(c)
        self.discard_pile.extend(self.hand)
        self.hand = []
        self.draw(5)

# ---------------------------
# Game
# ---------------------------
class Game:
    def __init__(self, players):
        self.players = players
        self.current_player = 0
        self.trade_deck = []
        self.trade_row = []

    def start(self, cardpool):
        self.trade_deck = list(cardpool)
        random.shuffle(self.trade_deck)
        self.trade_row = [self.trade_deck.pop() for _ in range(5)]
        for p in self.players:
            scouts = [Card("Scout", "None", 0, "ship", effects=[{"trade": 1}]) for _ in range(8)]
            vipers = [Card("Viper", "None", 0, "ship", effects=[{"combat": 1}]) for _ in range(2)]
            deck = scouts + vipers
            random.shuffle(deck)
            p.deck = deque(deck)
            p.draw(5)

    def get_current_player(self):
        return self.players[self.current_player]

    def next_player(self):
        self.current_player = (self.current_player + 1) % len(self.players)

# ---------------------------
# Effects
# ---------------------------
def run_effects(card, player, opponent, effects, game):
    for eff in effects:
        if "trade" in eff: player.trade += eff["trade"]
        if "combat" in eff: player.combat += eff["combat"]
        if "authority" in eff: player.authority += eff["authority"]
        if "draw" in eff: player.draw(eff["draw"])

def play_all_cards(player, opponent, game):
    for c in list(player.hand):
        player.hand.remove(c)
        player.in_play.append(c)
        run_effects(c, player, opponent, c.effects, game)

def attack(player, opponent):
    if player.combat > 0:
        opponent.authority -= player.combat
        print(f"{player.name} deals {player.combat} damage to {opponent.name}!")
        player.combat = 0

def buy_card(name, player, game):
    if name.lower() == "explorer":
        if player.trade >= 2:
            player.trade -= 2
            player.discard_pile.append(Card("Explorer", "None", 2, "ship",
                                            effects=[{"trade": 2}],
                                            scrap_effects=[{"combat": 2}]))
            print(f"{player.name} buys Explorer")
            return True
    else:
        for c in list(game.trade_row):
            if c.name.lower() == name.lower() and c.cost <= player.trade:
                player.trade -= c.cost
                player.discard_pile.append(c)
                game.trade_row.remove(c)
                if game.trade_deck:
                    game.trade_row.append(game.trade_deck.pop())
                print(f"{player.name} buys {c.name}")
                return True
    return False

# ---------------------------
# Trade Deck (tiny demo set)
# ---------------------------
BASE_TEST_SET = [
    Card("Battle Station", "Machine Cult", 3, "base", effects=[{"combat": 5}], defense=5, outpost=True),
    Card("Trading Post", "Trade Federation", 3, "base", effects=[{"trade": 1}], defense=4),
    Card("Blob Fighter", "Blob", 1, "ship", effects=[{"combat": 3}]),
    Card("Corvette", "Star Empire", 2, "ship", effects=[{"combat": 1}, {"draw": 1}]),
    Card("Freighter", "Trade Federation", 4, "ship", effects=[{"trade": 4}]),
    Card("Battle Pod", "Blob", 2, "ship", effects=[{"combat": 4}]),
    Card("Missile Bot", "Machine Cult", 2, "ship", effects=[{"combat": 2}]),
    Card("Survey Ship", "Star Empire", 3, "ship", effects=[{"trade": 1}, {"draw": 1}]),
] * 2