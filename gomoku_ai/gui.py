from __future__ import annotations

import os
import time
from dataclasses import dataclass, replace

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame

from gomoku_ai.core import BLACK, EMPTY, STONE_NAMES, opponent
from gomoku_ai.game import GameResult, GameSession, GameSettings, TurnOutcome, column_label, result_message

BACKGROUND = (238, 235, 226)
BOARD_FILL = (214, 169, 96)
BOARD_EDGE = (126, 82, 38)
GRID = (55, 42, 30)
BLACK_STONE = (25, 24, 22)
WHITE_STONE = (245, 241, 232)
WHITE_EDGE = (126, 119, 108)
ACCENT = (56, 106, 171)
ACCENT_DARK = (31, 70, 122)
PANEL = (250, 248, 241)
TEXT = (39, 38, 34)
MUTED = (103, 96, 86)
BUTTON = (232, 225, 213)
BUTTON_BORDER = (137, 123, 103)
DISABLED = (206, 200, 190)
BOARD_PADDING = 44


@dataclass(frozen=True)
class GuiLayout:
    size: int
    left: int
    top: int
    cell_size: int
    panel_left: int
    panel_width: int
    width: int
    height: int

    @property
    def board_pixels(self) -> int:
        return (self.size - 1) * self.cell_size


@dataclass(frozen=True)
class Button:
    action: str
    label: str
    rect: tuple[int, int, int, int]
    enabled: bool = True

    def contains(self, x: int, y: int) -> bool:
        left, top, width, height = self.rect
        return self.enabled and left <= x <= left + width and top <= y <= top + height


def create_layout(size: int) -> GuiLayout:
    cell_size = max(24, min(40, 520 // max(size - 1, 1)))
    left = 56
    top = 72
    panel_left = left + (size - 1) * cell_size + 64
    panel_width = 300
    width = panel_left + panel_width + 40
    height = max(top + (size - 1) * cell_size + 60, 620)
    return GuiLayout(
        size=size,
        left=left,
        top=top,
        cell_size=cell_size,
        panel_left=panel_left,
        panel_width=panel_width,
        width=width,
        height=height,
    )


def board_to_pixel(row: int, col: int, layout: GuiLayout) -> tuple[int, int]:
    return layout.left + col * layout.cell_size, layout.top + row * layout.cell_size


def row_label_rect(row: int, layout: GuiLayout, font: pygame.font.Font) -> pygame.Rect:
    _x, y = board_to_pixel(row, 0, layout)
    label = str(row + 1)
    rect = font.render(label, True, GRID).get_rect()
    rect.midright = (layout.left - 18, y)
    return rect


def pixel_to_board(x: int, y: int, layout: GuiLayout) -> tuple[int, int] | None:
    raw_col = (x - layout.left) / layout.cell_size
    raw_row = (y - layout.top) / layout.cell_size
    col = round(raw_col)
    row = round(raw_row)
    if not (0 <= row < layout.size and 0 <= col < layout.size):
        return None
    if abs(raw_col - col) > 0.42 or abs(raw_row - row) > 0.42:
        return None
    return row, col


def build_buttons(
    settings: GameSettings,
    result: GameResult | None,
    layout: GuiLayout,
    *,
    top: int = 300,
) -> list[Button]:
    buttons: list[Button] = []
    x = layout.panel_left
    width = layout.panel_width
    y = top
    row = 40

    if result is None:
        if settings.mode == "human-ai":
            buttons.append(Button("resign", "Resign", (x, y, width, 32)))
        else:
            buttons.append(Button("stop", "Stop", (x, y, width, 32)))
        y += row
        buttons.append(Button("restart", "Restart", (x, y, width, 32)))
        y += row
        buttons.append(Button("exit", "Exit", (x, y, width, 32)))
        return buttons

    if settings.mode == "human-ai":
        buttons.extend(
            [
                Button("depth_dec", "Difficulty -", (x, y, width // 2 - 6, 32)),
                Button("depth_inc", "Difficulty +", (x + width // 2 + 6, y, width // 2 - 6, 32)),
                Button("side_toggle", "Switch Side", (x, y + row, width, 32)),
            ]
        )
        y += row * 2
    else:
        half = width // 2 - 6
        buttons.extend(
            [
                Button("black_depth_dec", "Black -", (x, y, half, 32)),
                Button("black_depth_inc", "Black +", (x + width // 2 + 6, y, half, 32)),
                Button("white_depth_dec", "White -", (x, y + row, half, 32)),
                Button("white_depth_inc", "White +", (x + width // 2 + 6, y + row, half, 32)),
            ]
        )
        y += row * 2

    buttons.append(Button("restart", "Restart", (x, y, width, 32)))
    buttons.append(Button("exit", "Exit", (x, y + row, width, 32)))
    return buttons


def adjusted_settings(settings: GameSettings, action: str) -> GameSettings:
    if action == "depth_dec":
        return replace(settings, depth=_clamp_depth(settings.depth - 1))
    if action == "depth_inc":
        return replace(settings, depth=_clamp_depth(settings.depth + 1))
    if action == "black_depth_dec":
        return replace(settings, black_depth=_clamp_depth(settings.black_depth - 1))
    if action == "black_depth_inc":
        return replace(settings, black_depth=_clamp_depth(settings.black_depth + 1))
    if action == "white_depth_dec":
        return replace(settings, white_depth=_clamp_depth(settings.white_depth - 1))
    if action == "white_depth_inc":
        return replace(settings, white_depth=_clamp_depth(settings.white_depth + 1))
    if action == "side_toggle":
        return replace(settings, human_stone=opponent(settings.human_stone))
    return settings


def settings_lines(settings: GameSettings) -> list[str]:
    if settings.mode == "human-ai":
        return [
            f"Difficulty: {settings.depth}",
            f"Human: {STONE_NAMES[settings.human_stone]}",
        ]
    return [
        f"Black depth: {settings.black_depth}",
        f"White depth: {settings.white_depth}",
    ]


def panel_buttons_top(settings: GameSettings, status_line_count: int) -> int:
    return 62 + 48 + 28 + 28 + 36 + status_line_count * 22 + 12 + len(settings_lines(settings)) * 28 + 10


def play_gui(
    *,
    mode: str,
    size: int = 15,
    human_stone: int = BLACK,
    depth: int = 3,
    black_depth: int = 3,
    white_depth: int = 3,
    delay: float = 0.0,
    max_moves: int | None = None,
) -> GameResult:
    settings = GameSettings(
        mode=mode,
        size=size,
        human_stone=human_stone,
        depth=depth,
        black_depth=black_depth,
        white_depth=white_depth,
        max_moves=max_moves,
    )
    return PygameGomoku(settings=settings, delay=delay).run()


class PygameGomoku:
    def __init__(self, *, settings: GameSettings, delay: float = 0.0) -> None:
        pygame.init()
        self.settings = settings
        self.session = GameSession(settings)
        self.delay = delay
        self.layout = create_layout(settings.size)
        self.screen = pygame.display.set_mode((self.layout.width, self.layout.height))
        pygame.display.set_caption("Gomoku-AI")
        self.clock = pygame.time.Clock()
        self.title_font = pygame.font.SysFont("arial", 28, bold=True)
        self.font = pygame.font.SysFont("arial", 18)
        self.small_font = pygame.font.SysFont("arial", 15)
        self.message = "Black moves first."
        self.running = True
        self.last_ai_time = 0.0

    def run(self) -> GameResult:
        try:
            while self.running:
                self._handle_events()
                self._maybe_play_ai()
                self._draw()
                pygame.display.flip()
                self.clock.tick(60)
        finally:
            pygame.quit()

        if self.session.result is None:
            outcome = self.session.stop()
            assert outcome.result is not None
        assert self.session.result is not None
        return self.session.result

    def _handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_q):
                self.running = False
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self._handle_click(*event.pos)

    def _handle_click(self, x: int, y: int) -> None:
        for button in self._buttons():
            if button.contains(x, y):
                self._apply_action(button.action)
                return

        move = pixel_to_board(x, y, self.layout)
        if move is None or self.session.result is not None or self.session.is_ai_turn():
            return

        outcome = self.session.play_human_move(*move)
        self._apply_outcome(outcome)

    def _apply_action(self, action: str) -> None:
        if action == "exit":
            self.running = False
            return
        if action == "restart":
            self.session.restart(self.settings)
            self.message = "New game started."
            self.last_ai_time = 0.0
            return
        if action == "resign":
            self._apply_outcome(self.session.resign())
            return
        if action == "stop":
            self._apply_outcome(self.session.stop())
            return

        if self.session.result is not None:
            self.settings = adjusted_settings(self.settings, action)
            self.message = "Settings updated. Press Restart."

    def _maybe_play_ai(self) -> None:
        if self.session.result is not None or not self.session.is_ai_turn():
            return
        now = time.perf_counter()
        if self.settings.mode == "ai-ai":
            wait = max(self.delay, 0.05)
            if self.last_ai_time and now - self.last_ai_time < wait:
                return
        outcome = self.session.play_ai_move()
        self.last_ai_time = now
        self._apply_outcome(outcome)

    def _apply_outcome(self, outcome: TurnOutcome) -> None:
        if outcome.result is not None:
            self.message = result_message(outcome.result)
        else:
            self.message = outcome.message

    def _draw(self) -> None:
        self.screen.fill(BACKGROUND)
        self._draw_board()
        self._draw_panel()

    def _draw_board(self) -> None:
        board_rect = pygame.Rect(
            self.layout.left - BOARD_PADDING,
            self.layout.top - BOARD_PADDING,
            self.layout.board_pixels + BOARD_PADDING * 2,
            self.layout.board_pixels + BOARD_PADDING * 2,
        )
        pygame.draw.rect(self.screen, BOARD_FILL, board_rect, border_radius=6)
        pygame.draw.rect(self.screen, BOARD_EDGE, board_rect, width=2, border_radius=6)

        for index in range(self.layout.size):
            x = self.layout.left + index * self.layout.cell_size
            y = self.layout.top + index * self.layout.cell_size
            pygame.draw.line(self.screen, GRID, (self.layout.left, y), (self.layout.left + self.layout.board_pixels, y), 1)
            pygame.draw.line(self.screen, GRID, (x, self.layout.top), (x, self.layout.top + self.layout.board_pixels), 1)
            self._draw_text(column_label(index), (x - 7, self.layout.top - 24), self.small_font, GRID)
            self._draw_text(str(index + 1), row_label_rect(index, self.layout, self.small_font).topleft, self.small_font, GRID)

        for row in range(self.session.board.size):
            for col in range(self.session.board.size):
                stone = self.session.board.grid[row][col]
                if stone != EMPTY:
                    self._draw_stone(row, col, stone)

        if self.session.board.last_move is not None:
            row, col = self.session.board.last_move
            x, y = board_to_pixel(row, col, self.layout)
            pygame.draw.circle(self.screen, ACCENT, (x, y), max(5, self.layout.cell_size // 6), width=2)

    def _draw_stone(self, row: int, col: int, stone: int) -> None:
        x, y = board_to_pixel(row, col, self.layout)
        radius = max(8, self.layout.cell_size // 2 - 4)
        if stone == BLACK:
            pygame.draw.circle(self.screen, BLACK_STONE, (x, y), radius)
        else:
            pygame.draw.circle(self.screen, WHITE_EDGE, (x, y), radius)
            pygame.draw.circle(self.screen, WHITE_STONE, (x, y), radius - 2)

    def _draw_panel(self) -> None:
        panel_rect = pygame.Rect(self.layout.panel_left - 20, 36, self.layout.panel_width + 40, self.layout.height - 72)
        pygame.draw.rect(self.screen, PANEL, panel_rect, border_radius=8)
        pygame.draw.rect(self.screen, BUTTON_BORDER, panel_rect, width=1, border_radius=8)

        y = 62
        self._draw_text("Gomoku-AI", (self.layout.panel_left, y), self.title_font, TEXT)
        y += 48
        self._draw_text(f"Mode: {self._mode_label()}", (self.layout.panel_left, y), self.font, TEXT)
        y += 28
        self._draw_text(f"Turn: {STONE_NAMES[self.session.current]}", (self.layout.panel_left, y), self.font, TEXT)
        y += 28
        self._draw_text(f"Moves: {self.session.board.move_count}", (self.layout.panel_left, y), self.font, TEXT)
        y += 36
        for line in self._status_lines():
            self._draw_text(line, (self.layout.panel_left, y), self.small_font, MUTED)
            y += 22

        y += 12
        for line in settings_lines(self.settings):
            self._draw_text(line, (self.layout.panel_left, y), self.font, TEXT)
            y += 28

        for button in self._buttons():
            self._draw_button(button)

        if self.session.result is not None:
            self._draw_text("Settlement", (self.layout.panel_left, self.layout.height - 90), self.font, ACCENT_DARK)
            self._draw_text("Adjust settings, then restart.", (self.layout.panel_left, self.layout.height - 62), self.small_font, MUTED)

    def _draw_button(self, button: Button) -> None:
        rect = pygame.Rect(button.rect)
        fill = BUTTON if button.enabled else DISABLED
        pygame.draw.rect(self.screen, fill, rect, border_radius=5)
        pygame.draw.rect(self.screen, BUTTON_BORDER, rect, width=1, border_radius=5)
        surface = self.font.render(button.label, True, TEXT if button.enabled else MUTED)
        text_rect = surface.get_rect(center=rect.center)
        self.screen.blit(surface, text_rect)

    def _draw_text(self, text: str, pos: tuple[int, int], font: pygame.font.Font, color: tuple[int, int, int]) -> None:
        surface = font.render(text, True, color)
        self.screen.blit(surface, pos)

    def _buttons(self) -> list[Button]:
        return build_buttons(
            self.settings,
            self.session.result,
            self.layout,
            top=panel_buttons_top(self.settings, len(self._status_lines())),
        )

    def _status_lines(self) -> list[str]:
        if len(self.message) <= 32:
            return [self.message]
        words = self.message.split()
        lines: list[str] = []
        current = ""
        for word in words:
            candidate = f"{current} {word}".strip()
            if len(candidate) > 32:
                lines.append(current)
                current = word
            else:
                current = candidate
        if current:
            lines.append(current)
        return lines[:3]

    def _mode_label(self) -> str:
        return "Human vs AI" if self.settings.mode == "human-ai" else "AI vs AI"


def _clamp_depth(depth: int) -> int:
    return min(max(depth, 1), 5)
