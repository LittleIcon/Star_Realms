# starrealms/agent/ai.py
from .base import Agent


class SimpleAgent(Agent):
    # Example heuristic used only if wired in later
    def choose_scrap_hand_or_discard(self, game):
        p = self.player
        if getattr(p, "discard_pile", None):
            return ("discard", 0)
        if getattr(p, "hand", None):
            return ("hand", 0)
        return None
