# starrealms/graphics/pygame_view.py
# Minimal Pygame view for Star Realms.
# Assumes your engine exposes:
#   Game(("P1","P2")) with .current_player(), .opponent(), .trade_row
#   Player with .hand, .in_play, .bases, .authority, .trade_pool, .combat_pool
#   Engine methods (adapt as needed): game.play_card(index), game.buy_card(index), game.end_turn()
# If your engine uses different calls, adapt the _actions section near the bottom.

import pygame
from typing import List, Tuple, Dict, Optional

CARD_W, CARD_H = 120, 170
PADDING = 10
FONT_SIZE = 18
BG = (18, 24, 32)
PANEL = (30, 38, 50)
PANEL_HL = (45, 60, 80)
TEXT = (235, 238, 240)
ACCENT = (70, 170, 255)
RED = (230, 70, 70)
GREEN = (60, 185, 110)
YELLOW = (235, 210, 80)
GRAY = (120, 120, 130)

FACTION_COLORS = {
    "Machine Cult": (200, 80, 60),
    "Blob": (90, 200, 90),
    "Trade Federation": (70, 160, 230),
    "Star Empire": (235, 215, 60),
    "Neutral": (160, 160, 170),
}

def safe_name(c: Dict) -> str: return c.get("name", "?")
def safe_faction(c: Dict) -> str: return c.get("faction", "Neutral")
def safe_cost(c: Dict) -> int:
    try: return int(c.get("cost", 0) or 0)
    except: return 0
def is_outpost(c: Dict) -> bool: return bool(c.get("outpost"))

class CardView:
    def __init__(self, rect: pygame.Rect, zone: str, index: int, card: Dict):
        self.rect = rect
        self.zone = zone  # "hand" | "trade" | "in_play" | "bases" | "op_bases"
        self.index = index
        self.card = card

class StarRealmsPygameView:
    def __init__(self, game, w=1280, h=800, fps=60):
        pygame.init()
        pygame.display.set_caption("Star Realms (Pygame)")
        self.screen = pygame.display.set_mode((w, h))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont(None, FONT_SIZE)
        self.big = pygame.font.SysFont(None, 26)
        self.game = game
        self.fps = fps
        self.hover: Optional[CardView] = None
        self.message: str = ""
        self.views: List[CardView] = []

    # ---------- Layout helpers ----------
    def _layout_row(self, cards: List[Dict], start_y: int, zone: str, left_margin=10) -> List[CardView]:
        x = left_margin
        rendered = []
        for i, c in enumerate(cards):
            r = pygame.Rect(x, start_y, CARD_W, CARD_H)
            rendered.append(CardView(r, zone, i, c))
            x += CARD_W + PADDING
        return rendered

    def _draw_card(self, cv: CardView, highlight=False):
        c = cv.card
        name = safe_name(c)
        faction = safe_faction(c)
        cost = safe_cost(c)
        fac_color = FACTION_COLORS.get(faction, GRAY)
        # panel
        color = PANEL_HL if highlight else PANEL
        pygame.draw.rect(self.screen, color, cv.rect, border_radius=12)
        # faction stripe
        stripe = cv.rect.copy()
        stripe.height = 22
        pygame.draw.rect(self.screen, fac_color, stripe, border_radius=12)
        # name
        txt = self.font.render(name, True, TEXT)
        self.screen.blit(txt, (cv.rect.x + 8, cv.rect.y + 26))
        # cost badge
        badge = pygame.Rect(cv.rect.right - 32, cv.rect.y + 6, 26, 26)
        pygame.draw.ellipse(self.screen, YELLOW, badge)
        cost_surf = self.font.render(str(cost), True, (20, 20, 20))
        self.screen.blit(cost_surf, (badge.x + 8, badge.y + 4))
        # outpost banner
        if is_outpost(c):
            tag = self.font.render("OUTPOST", True, TEXT)
            self.screen.blit(tag, (cv.rect.x + 8, cv.rect.bottom - 24))

    def _draw_panel(self, rect: pygame.Rect, label: str, value_surf: Optional[pygame.Surface] = None, color=PANEL):
        pygame.draw.rect(self.screen, color, rect, border_radius=12)
        lab = self.big.render(label, True, TEXT)
        self.screen.blit(lab, (rect.x + 12, rect.y + 10))
        if value_surf:
            self.screen.blit(value_surf, (rect.right - value_surf.get_width() - 12, rect.y + 12))

    # ---------- Render ----------
    def render(self):
        self.screen.fill(BG)
        self.views = []

        p = self.game.current_player()
        o = self.game.opponent()

        # Top: opponent panels
        opp_panel = pygame.Rect(10, 10, 380, 80)
        opp_stats = self.font.render(
            f"Authority {o.authority}  |  Bases {len(getattr(o, 'bases', []))}", True, TEXT)
        self._draw_panel(opp_panel, "Opponent", opp_stats)

        # Opponent bases
        ob_start = opp_panel.bottom + 10
        ob_views = self._layout_row(getattr(o, "bases", []), ob_start, "op_bases")
        self.views.extend(ob_views)
        for cv in ob_views:
            self._draw_card(cv, highlight=(self.hover is cv))

        # Trade row
        tr_label = pygame.Rect(10, 200, 780, 40)
        self._draw_panel(tr_label, "Trade Row")
        tr_views = self._layout_row(getattr(self.game, "trade_row", []), tr_label.bottom + 10, "trade")
        self.views.extend(tr_views)
        for cv in tr_views:
            self._draw_card(cv, highlight=(self.hover is cv))

        # In Play
        ip_label = pygame.Rect(10, 430, 780, 40)
        self._draw_panel(ip_label, "In Play")
        ip_views = self._layout_row(getattr(p, "in_play", []), ip_label.bottom + 10, "in_play")
        self.views.extend(ip_views)
        for cv in ip_views:
            self._draw_card(cv, highlight=(self.hover is cv))

        # Player bases
        pb_label = pygame.Rect(10, 610, 780, 40)
        self._draw_panel(pb_label, "Your Bases")
        pb_views = self._layout_row(getattr(p, "bases", []), pb_label.bottom + 10, "bases")
        self.views.extend(pb_views)
        for cv in pb_views:
            self._draw_card(cv, highlight=(self.hover is cv))

        # Hand (right side)
        hand_panel = pygame.Rect(820, 10, 450, 40)
        self._draw_panel(hand_panel, "Your Hand")
        h_views = self._layout_row(getattr(p, "hand", []), hand_panel.bottom + 10, "hand", left_margin=820)
        self.views.extend(h_views)
        for cv in h_views:
            self._draw_card(cv, highlight=(self.hover is cv))

        # Stats & controls
        stats_panel = pygame.Rect(820, 430, 450, 220)
        pv = self.font.render(
            f"Authority: {p.authority}   Trade: {getattr(p, 'trade_pool', 0)}   Combat: {getattr(p, 'combat_pool', 0)}",
            True, TEXT
        )
        self._draw_panel(stats_panel, "Status", pv)

        # Buttons
        self.btn_end = pygame.Rect(stats_panel.x + 18, stats_panel.bottom - 56, 150, 40)
        self.btn_play_all = pygame.Rect(stats_panel.x + 190, stats_panel.bottom - 56, 150, 40)
        self._button(self.btn_end, "End Turn")
        self._button(self.btn_play_all, "Play All")

        # Message line
        if self.message:
            msg = self.font.render(self.message, True, ACCENT)
            self.screen.blit(msg, (820, 670))

        pygame.display.flip()

    def _button(self, rect: pygame.Rect, label: str):
        pygame.draw.rect(self.screen, (52, 64, 78), rect, border_radius=10)
        txt = self.font.render(label, True, TEXT)
        self.screen.blit(txt, (rect.centerx - txt.get_width()//2, rect.centery - txt.get_height()//2))

    # ---------- Interaction ----------
    def _card_under_mouse(self, pos) -> Optional[CardView]:
        for cv in self.views:
            if cv.rect.collidepoint(pos):
                return cv
        return None

    def loop(self):
        running = True
        while running:
            dt = self.clock.tick(self.fps)
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    running = False
                elif e.type == pygame.MOUSEMOTION:
                    self.hover = self._card_under_mouse(e.pos)
                elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                    if self.btn_end.collidepoint(e.pos):
                        self._action_end_turn()
                    elif self.btn_play_all.collidepoint(e.pos):
                        self._action_play_all()
                    else:
                        cv = self._card_under_mouse(e.pos)
                        if cv:
                            self._handle_card_click(cv)

                elif e.type == pygame.KEYDOWN:
                    if e.key == pygame.K_ESCAPE:
                        running = False
                    elif e.key == pygame.K_RETURN:
                        self._action_end_turn()

            self.render()
        pygame.quit()

    # ---------- Actions (ADAPT TO YOUR ENGINE) ----------
    def _handle_card_click(self, cv: CardView):
        try:
            if cv.zone == "hand":
                # Play the selected card by index in hand
                self._action_play_card(cv.index)
            elif cv.zone == "trade":
                # Buy from trade row (index)
                self._action_buy_card(cv.index)
            elif cv.zone in ("bases", "in_play", "op_bases"):
                # Future: target for abilities / attack base, etc.
                self.message = "Clicked card in zone: " + cv.zone
        except Exception as ex:
            self.message = f"Error: {ex}"

    def _action_play_card(self, idx: int):
        # Your engine may expose: self.game.play_card(idx) or player_play
        # If you require a card reference, grab current_player().hand[idx].
        if hasattr(self.game, "play_card"):
            self.game.play_card(idx)
        else:
            # Fallback: directly move hand card to in_play
            p = self.game.current_player()
            if 0 <= idx < len(p.hand):
                card = p.hand.pop(idx)
                p.in_play.append(card)
        self.message = "Played card"

    def _action_buy_card(self, idx: int):
        # Your engine may expose: self.game.buy_card(idx)
        if hasattr(self.game, "buy_card"):
            self.game.buy_card(idx)
            self.message = "Bought card"
            return

        # Fallback: naive buy if enough trade_pool
        p = self.game.current_player()
        tr = getattr(self.game, "trade_row", [])
        if 0 <= idx < len(tr):
            card = tr[idx]
            cost = safe_cost(card)
            if getattr(p, "trade_pool", 0) >= cost:
                p.trade_pool -= cost
                bought = tr.pop(idx)
                p.discard.append(bought) if hasattr(p, "discard") else p.hand.append(bought)
                self.message = f"Bought {safe_name(bought)}"
            else:
                self.message = "Not enough trade"

    def _action_end_turn(self):
        if hasattr(self.game, "end_turn"):
            self.game.end_turn()
        else:
            self.message = "end_turn() not implemented"
        self.message = "Turn ended"

    def _action_play_all(self):
        p = self.game.current_player()
        # Try engine method first
        if hasattr(self.game, "play_all"):
            self.game.play_all()
            self.message = "Played all"
            return
        # fallback: dump all hand into in_play
        while getattr(p, "hand", []):
            self._action_play_card(0)
        self.message = "Played all"