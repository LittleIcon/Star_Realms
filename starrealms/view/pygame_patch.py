# starrealms/view/pygame_patch.py
import pygame
import starrealms.view.ui_common as ui_common


class LogPanel:
    def __init__(
        self,
        size=(900, 600),
        bg=(12, 12, 14),
        fg=(230, 230, 230),
        font_name="DejaVu Sans Mono",
        font_size=18,
    ):
        pygame.init()
        self.screen = pygame.display.set_mode(size)
        pygame.display.set_caption("Star Realms (pygame log)")
        self.clock = pygame.time.Clock()
        self.bg, self.fg = bg, fg
        self.font = pygame.font.SysFont(font_name, font_size)
        self.margin = 12
        self.line_height = self.font.get_height() + 2
        self.max_lines = (size[1] - 2 * self.margin) // self.line_height
        self.lines = []

    def add_line(self, text: str):
        t = str(text).rstrip()
        if not t:
            return
        self.lines.append(t)
        if len(self.lines) > 5000:
            self.lines = self.lines[-5000:]

    def draw(self):
        self.screen.fill(self.bg)
        view = self.lines[-self.max_lines :]
        y = self.margin
        for line in view:
            surf = self.font.render(line, True, self.fg)
            self.screen.blit(surf, (self.margin, y))
            y += self.line_height
        pygame.display.flip()

    def tick(self, fps=30):
        self.clock.tick(fps)


def apply(panel: LogPanel):
    """Monkey-patch ui_common so engine logs go to pygame."""

    def _ui_print(*args, **kwargs):
        panel.add_line(" ".join(str(a) for a in args))

    def _ui_log(game, message: str):
        if getattr(game, "log", None) is not None:
            game.log.append(message)
        _ui_print(message)

    ui_common.ui_print = _ui_print
    ui_common.ui_log = _ui_log
