# pygame_main.py
import sys
import time
import builtins
import pygame

import starrealms.view.ui_common as ui_common

# --------------------- Config ---------------------
WINDOW_W, WINDOW_H = 1280, 720
FONT_SIZE = 24
LINE_SPACING = 4
MAX_LINES = 8000
ECHO_TO_CONSOLE = True   # also mirror to Termux console for now
# --------------------------------------------------

def _now():
    return time.strftime("%H:%M:%S")

class LogPanel:
    def __init__(self, size=(WINDOW_W, WINDOW_H), bg=(12, 12, 14)):
        pygame.init()
        self.screen = pygame.display.set_mode(size, pygame.RESIZABLE)
        pygame.display.set_caption("Star Realms (pygame)")
        self.clock = pygame.time.Clock()
        self.bg = bg

        self.font_size = FONT_SIZE
        self.font = pygame.font.Font(None, self.font_size)

        self.margin = 16
        self.lines: list[tuple[str, pygame.Color]] = []   # (text, color)
        self.input_text = ""
        self.prompt = "> "
        self.entered: str | None = None
        self.history: list[str] = []
        self.history_idx: int | None = None

        # scrolling
        self.scroll_offset = 0     # how many rendered rows from the bottom we’re scrolled up
        self._recompute_metrics()

    # -------- metrics & rendering ----------
    def _recompute_metrics(self):
        w, h = self.screen.get_size()
        self.width = w
        self.line_height = self.font.get_height() + LINE_SPACING
        self.input_y = h - self.margin - self.font.get_height()
        usable_h = h - (2 * self.margin) - (self.font.get_height() + 10)
        self.max_visible = max(1, usable_h // self.line_height)

    def set_font_size(self, size: int):
        self.font_size = max(12, min(48, size))
        self.font = pygame.font.Font(None, self.font_size)
        self._recompute_metrics()

    def _wrap(self, text: str) -> list[str]:
        words = text.split(" ")
        out, cur = [], ""
        max_w = self.width - 2 * self.margin
        for w in words:
            test = (cur + " " + w).strip()
            if self.font.size(test)[0] > max_w:
                if cur:
                    out.append(cur)
                cur = w
            else:
                cur = test
        if cur:
            out.append(cur)
        return out

    def _color_for(self, line: str) -> pygame.Color:
        s = line.lower()
        if "blob" in s:
            return pygame.Color(120, 220, 120)
        if "star empire" in s or "(se" in s:
            return pygame.Color(240, 220, 120)
        if "machine cult" in s or "(mc" in s:
            return pygame.Color(235, 140, 140)
        if "trade federation" in s or "(tf" in s:
            return pygame.Color(140, 180, 235)
        if "explorer" in s:
            return pygame.Color(200, 200, 255)
        return pygame.Color(230, 230, 230)

    def add_line(self, text: str):
        text = str(text).rstrip()
        if not text:
            return
        color = self._color_for(text)
        wrapped = self._wrap(text)
        # if we are at bottom (no scroll), keep following new lines automatically
        at_bottom = (self.scroll_offset == 0)
        for w in wrapped:
            self.lines.append((w, color))
        if len(self.lines) > MAX_LINES:
            self.lines = self.lines[-MAX_LINES:]
        if at_bottom:
            self.scroll_offset = 0  # new lines -> stay at bottom

    def draw(self):
        self.screen.fill(self.bg)

        # compute slice with scrollback
        start = max(0, len(self.lines) - self.max_visible - self.scroll_offset)
        end = start + self.max_visible
        view = self.lines[start:end]

        y = self.margin
        for text, color in view:
            surf = self.font.render(text, True, color)
            self.screen.blit(surf, (self.margin, y))
            y += self.line_height

        # input line
        prompt = self.prompt + self.input_text
        surf = self.font.render(prompt, True, pygame.Color(180, 220, 180))
        self.screen.blit(surf, (self.margin, self.input_y))

        pygame.display.flip()

    def tick(self, fps=30):
        self.clock.tick(fps)

    # -------- input / history / scroll ----------
    def _commit_input(self):
        self.entered = self.input_text
        if self.input_text:
            self.history.append(self.input_text)
        self.history_idx = None
        self.add_line(self.prompt + self.input_text)
        self.input_text = ""

    def handle_event(self, e):
        if e.type == pygame.VIDEORESIZE:
            self.screen = pygame.display.set_mode((e.w, e.h), pygame.RESIZABLE)
            self._recompute_metrics()
        elif e.type == pygame.MOUSEWHEEL:
            # up is positive on pygame 2.1+
            self.scroll_offset = max(0, self.scroll_offset - e.y)
        elif e.type == pygame.KEYDOWN:
            mods = pygame.key.get_mods()
            ctrl = bool(mods & pygame.KMOD_CTRL)

            if e.key == pygame.K_RETURN:
                self._commit_input()
            elif e.key == pygame.K_BACKSPACE:
                self.input_text = self.input_text[:-1]
            elif e.key == pygame.K_UP:
                if self.history:
                    if self.history_idx is None:
                        self.history_idx = len(self.history) - 1
                    else:
                        self.history_idx = max(0, self.history_idx - 1)
                    self.input_text = self.history[self.history_idx]
            elif e.key == pygame.K_DOWN:
                if self.history:
                    if self.history_idx is None:
                        self.input_text = ""
                    else:
                        self.history_idx += 1
                        if self.history_idx >= len(self.history):
                            self.history_idx = None
                            self.input_text = ""
                        else:
                            self.input_text = self.history[self.history_idx]
            elif e.key == pygame.K_PAGEUP:
                self.scroll_offset = min(len(self.lines), self.scroll_offset + self.max_visible // 2)
            elif e.key == pygame.K_PAGEDOWN:
                self.scroll_offset = max(0, self.scroll_offset - self.max_visible // 2)
            elif e.key in (pygame.K_ESCAPE, pygame.K_q):
                pygame.event.post(pygame.event.Event(pygame.QUIT))
            elif ctrl and e.key in (pygame.K_EQUALS, pygame.K_PLUS):
                self.set_font_size(self.font_size + 2)
            elif ctrl and e.key == pygame.K_MINUS:
                self.set_font_size(self.font_size - 2)
            elif ctrl and e.key == pygame.K_0:
                self.set_font_size(FONT_SIZE)
            elif ctrl and e.key == pygame.K_l:
                self.lines.clear()
            elif ctrl and e.key == pygame.K_s:
                with open("pygame_log.txt", "w", encoding="utf-8") as f:
                    for t, _c in self.lines:
                        f.write(t + "\n")
                self.add_line(f"[{_now()}] Saved log to pygame_log.txt")
            else:
                if e.unicode and e.key < 256:
                    self.input_text += e.unicode

    def poll_input(self):
        if self.entered is not None:
            s = self.entered
            self.entered = None
            return s
        return None


# ------------- UI shims -> pygame -------------
log_panel = LogPanel()

def pygame_ui_print(*args, **kwargs):
    log_panel.add_line(" ".join(str(a) for a in args))

def pygame_ui_log(game, message: str):
    if getattr(game, "log", None) is not None:
        game.log.append(message)
    pygame_ui_print(message)

def pygame_ui_input(prompt: str = "") -> str:
    if prompt:
        log_panel.add_line(prompt)
    while True:
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit(); sys.exit(0)
            log_panel.handle_event(e)

        ans = log_panel.poll_input()
        if ans is not None:
            return ans

        log_panel.draw()
        log_panel.tick(60)

# Patch ui_common
ui_common.ui_print = pygame_ui_print
ui_common.ui_log = pygame_ui_log
ui_common.ui_input = pygame_ui_input

# Mirror stray print() calls into the panel (and console if enabled)
_old_print = builtins.print
def _print_to_both(*args, **kwargs):
    pygame_ui_print(" ".join(str(a) for a in args))
    if ECHO_TO_CONSOLE:
        _old_print(*args, **kwargs)
builtins.print = _print_to_both
# ----------------------------------------------

def main():
    from starrealms.game import Game
    from starrealms.runner.human import human_turn

    g = Game(("You", "AI"))
    log_panel.add_line("Pygame UI ready. Starting a game…")
    last_log = 0

    while not g.check_winner():
        last_log = human_turn(g, last_log)
        log_panel.draw()
        log_panel.tick(60)

    w = g.check_winner()
    pygame_ui_print(f"Winner: {w.name if w else 'Unknown'}")
    pygame.time.wait(2000)

if __name__ == "__main__":
    main()