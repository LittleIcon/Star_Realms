# starrealms/agent/base.py
class Agent:
    def __init__(self, player):
        self.player = player

    # Optional hook: return ("hand" or "discard", index) or None to skip.
    def choose_scrap_hand_or_discard(self, game):
        return None
