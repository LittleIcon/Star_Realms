# starrealms/agent/simple_ai.py
from .base import Agent

class SimpleAIAgent(Agent):
    # Basic heuristic used only if wired in
    def choose_scrap_hand_or_discard(self, game):
        p = self.player
        if getattr(p, "discard_pile", None):
            return ("discard", 0)  # prefer scrapping from discard
        if getattr(p, "hand", None):
            return ("hand", 0)
        return None