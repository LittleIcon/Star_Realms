# starrealms/agent/base.py
class Agent:
    def __init__(self, player):
        self.player = player

    # Hooks return either a decision or None (skip)
    def choose_scrap_hand_or_discard(self, game):
        return None