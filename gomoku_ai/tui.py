from __future__ import annotations

import curses
from dataclasses import dataclass

from gomoku_ai.core import BLACK, EMPTY, STONE_LABELS, STONE_NAMES, opponent
from gomoku_ai.game import (
    MAX_UI_DEPTH,
    MIN_UI_DEPTH,
    GameResult,
    GameSession,
    GameSettings,
    column_label,
    format_move,
    result_message,
)


@dataclass(frozen=True)
class BoardGeometry:
    top: int = 3
    left: int = 5
    cell_width: int = 3


def board_to_screen(row: int, col: int, geometry: BoardGeometry = BoardGeometry()) -> tuple[int, int]:
    return geometry.top + 1 + row, geometry.left + col * geometry.cell_width


def screen_to_board(
    y: int,
    x: int,
    *,
    size: int,
    geometry: BoardGeometry = BoardGeometry(),
) -> tuple[int, int] | None:
    row = y - geometry.top - 1
    if not 0 <= row < size:
        return None

    raw_col = x - geometry.left
    col = round(raw_col / geometry.cell_width)
    if not 0 <= col < size:
        return None
    if abs(raw_col - col * geometry.cell_width) > 1:
        return None
    return row, col


def play_tui(
    *,
    mode: str,
    size: int = 15,
    human_stone: int = BLACK,
    ai_algorithm: str = "v4",
    depth: int = 4,
    black_algorithm: str = "v4",
    white_algorithm: str = "v4",
    black_depth: int = 4,
    white_depth: int = 4,
    delay: float = 0.0,
    max_moves: int | None = None,
) -> GameResult:
    return curses.wrapper(
        _run_tui,
        mode,
        size,
        human_stone,
        ai_algorithm,
        depth,
        black_algorithm,
        white_algorithm,
        black_depth,
        white_depth,
        delay,
        max_moves,
    )


def _run_tui(
    stdscr: curses.window,
    mode: str,
    size: int,
    human_stone: int,
    ai_algorithm: str,
    depth: int,
    black_algorithm: str,
    white_algorithm: str,
    black_depth: int,
    white_depth: int,
    delay: float,
    max_moves: int | None,
) -> GameResult:
    game = _TuiGame(
        stdscr=stdscr,
        mode=mode,
        size=size,
        human_stone=human_stone,
        ai_algorithm=ai_algorithm,
        depth=depth,
        black_algorithm=black_algorithm,
        white_algorithm=white_algorithm,
        black_depth=black_depth,
        white_depth=white_depth,
        delay=delay,
        max_moves=max_moves,
    )
    return game.play()


class _TuiGame:
    def __init__(
        self,
        *,
        stdscr: curses.window,
        mode: str,
        size: int,
        human_stone: int,
        ai_algorithm: str,
        depth: int,
        black_algorithm: str,
        white_algorithm: str,
        black_depth: int,
        white_depth: int,
        delay: float,
        max_moves: int | None,
    ) -> None:
        self.stdscr = stdscr
        self.mode = mode
        self.size = size
        self.ai_algorithm = ai_algorithm
        self.depth = depth
        self.black_algorithm = black_algorithm
        self.white_algorithm = white_algorithm
        self.black_depth = black_depth
        self.white_depth = white_depth
        self.human_stone = human_stone
        self.cursor = (size // 2, size // 2)
        self.geometry = BoardGeometry()
        self.delay = delay
        self.max_moves = max_moves
        self.message = "Arrows move, Space/Enter places, mouse click places, q quits."
        self.session = GameSession(self._settings())

    @property
    def board(self):
        return self.session.board

    @property
    def current(self) -> int:
        return self.session.current

    def play(self) -> GameResult:
        curses.curs_set(0)
        self.stdscr.keypad(True)
        curses.mousemask(curses.ALL_MOUSE_EVENTS)
        curses.mouseinterval(0)

        while True:
            self._reset_for_new_game()
            result = self._play_single_game()
            if not self._settlement_menu(result):
                return result

    def _play_single_game(self) -> GameResult:
        while self.max_moves is None or self.board.move_count < self.max_moves:
            if self._is_ai_turn():
                result = self._play_ai_turn()
                if result is not None:
                    return result
                continue

            self._draw()
            key = self.stdscr.getch()
            if key in (ord("q"), ord("Q")):
                return self._finish(opponent(self.human_stone), resigned=True)
            if key == curses.KEY_MOUSE:
                move = self._mouse_move()
                if move is not None:
                    result = self._place_current(*move)
                    if result is not None:
                        return result
                continue
            if key in (curses.KEY_UP, ord("k"), ord("K")):
                self._move_cursor(-1, 0)
            elif key in (curses.KEY_DOWN, ord("j"), ord("J")):
                self._move_cursor(1, 0)
            elif key in (curses.KEY_LEFT, ord("h"), ord("H")):
                self._move_cursor(0, -1)
            elif key in (curses.KEY_RIGHT, ord("l"), ord("L")):
                self._move_cursor(0, 1)
            elif key in (ord(" "), ord("\n"), ord("\r"), curses.KEY_ENTER):
                result = self._place_current(*self.cursor)
                if result is not None:
                    return result

        return self._finish(None)

    def _reset_for_new_game(self) -> None:
        self.session.restart(self._settings())
        self.cursor = (self.size // 2, self.size // 2)
        self.message = "Arrows move, Space/Enter places, mouse click places, q quits."

    def _settings(self) -> GameSettings:
        return GameSettings(
            mode=self.mode,
            size=self.size,
            human_stone=self.human_stone,
            ai_algorithm=self.ai_algorithm,
            black_algorithm=self.black_algorithm,
            white_algorithm=self.white_algorithm,
            depth=self.depth,
            black_depth=self.black_depth,
            white_depth=self.white_depth,
            max_moves=self.max_moves,
        )

    def _is_ai_turn(self) -> bool:
        return self.session.is_ai_turn()

    def _play_ai_turn(self) -> GameResult | None:
        self.message = f"AI ({STONE_NAMES[self.current]}) thinking..."
        self._draw()
        outcome = self.session.play_ai_move()
        if outcome.move is not None:
            self.cursor = outcome.move
        self.message = outcome.message
        if outcome.result is not None:
            self.message = result_message(outcome.result)
            return outcome.result
        if self.delay > 0:
            self._draw()
            self.stdscr.timeout(int(self.delay * 1000))
            key = self.stdscr.getch()
            self.stdscr.timeout(-1)
            if key in (ord("q"), ord("Q")):
                return self._finish(None)
        elif self.mode == "ai-ai":
            self.stdscr.timeout(1)
            key = self.stdscr.getch()
            self.stdscr.timeout(-1)
            if key in (ord("q"), ord("Q")):
                return self._finish(None)
        return None

    def _place_current(self, row: int, col: int) -> GameResult | None:
        outcome = self.session.play_human_move(row, col)
        if outcome.move is not None:
            self.cursor = outcome.move
        self.message = outcome.message
        if outcome.result is not None:
            self.message = result_message(outcome.result)
            return outcome.result
        return None

    def _finish(self, winner: int | None, *, resigned: bool = False) -> GameResult:
        outcome = self.session.finish(winner, resigned=resigned)
        assert outcome.result is not None
        self.message = result_message(outcome.result)
        return outcome.result

    def _settlement_menu(self, result: GameResult) -> bool:
        try:
            curses.flushinp()
        except curses.error:
            pass

        selected = 0
        self.stdscr.timeout(-1)
        while True:
            entries = self._settlement_entries()
            self._draw_settlement(entries, selected, result)
            key = self.stdscr.getch()

            if key in (ord("q"), ord("Q")):
                return False
            if key in (curses.KEY_UP, ord("k"), ord("K")):
                selected = (selected - 1) % len(entries)
            elif key in (curses.KEY_DOWN, ord("j"), ord("J")):
                selected = (selected + 1) % len(entries)
            elif key in (curses.KEY_LEFT, curses.KEY_RIGHT, ord(" "), ord("\n"), ord("\r"), curses.KEY_ENTER):
                action = entries[selected][0]
                direction = -1 if key == curses.KEY_LEFT else 1
                if action == "depth":
                    self.depth = _clamp_depth(self.depth + direction)
                elif action == "black_depth":
                    self.black_depth = _clamp_depth(self.black_depth + direction)
                elif action == "white_depth":
                    self.white_depth = _clamp_depth(self.white_depth + direction)
                elif action == "side":
                    self.human_stone = opponent(self.human_stone)
                elif action == "restart":
                    return True
                elif action == "exit":
                    return False

    def _settlement_entries(self) -> list[tuple[str, str]]:
        if self.mode == "ai-ai":
            return [
                ("black_depth", f"Black AI depth: {self.black_depth}"),
                ("white_depth", f"White AI depth: {self.white_depth}"),
                ("restart", "Restart"),
                ("exit", "Exit"),
            ]
        return [
            ("depth", f"Difficulty: {self.depth}"),
            ("side", f"Your side: {STONE_NAMES[self.human_stone]}"),
            ("restart", "Restart"),
            ("exit", "Exit"),
        ]

    def _draw_settlement(
        self,
        entries: list[tuple[str, str]],
        selected: int,
        result: GameResult,
    ) -> None:
        self._draw()
        panel_x = self.geometry.left + self.board.size * self.geometry.cell_width + 2
        panel_y = self.geometry.top + 1
        self._safe_addstr(panel_y, panel_x, "Result")
        self._safe_addstr(panel_y + 1, panel_x, self.message)
        self._safe_addstr(panel_y + 2, panel_x, f"Moves: {result.moves}")
        self._safe_addstr(panel_y + 3, panel_x, f"Time: {result.elapsed:.2f}s")
        self._safe_addstr(panel_y + 5, panel_x, "Settlement")
        for index, (_action, label) in enumerate(entries):
            attr = curses.A_REVERSE if index == selected else curses.A_NORMAL
            self._safe_addstr(panel_y + 6 + index, panel_x, label, attr)
        self._safe_addstr(
            self.geometry.top + self.board.size + 4,
            0,
            "Settlement: Up/Down select | Left/Right change | Enter confirm | q exit",
        )
        self.stdscr.refresh()

    def _mouse_move(self) -> tuple[int, int] | None:
        try:
            _mouse_id, x, y, _z, button_state = curses.getmouse()
        except curses.error:
            return None
        if not button_state & (curses.BUTTON1_CLICKED | curses.BUTTON1_PRESSED | curses.BUTTON1_RELEASED):
            return None
        move = screen_to_board(y, x, size=self.board.size, geometry=self.geometry)
        if move is None:
            self.message = "Click inside the board."
            return None
        if not self.board.is_empty_at(*move):
            self.message = "That point is already occupied."
            return None
        self.cursor = move
        return move

    def _move_cursor(self, row_delta: int, col_delta: int) -> None:
        row, col = self.cursor
        row = min(max(row + row_delta, 0), self.board.size - 1)
        col = min(max(col + col_delta, 0), self.board.size - 1)
        self.cursor = (row, col)

    def _draw(self) -> None:
        self.stdscr.erase()
        height, width = self.stdscr.getmaxyx()
        required_height = self.geometry.top + self.board.size + 7
        required_width = self.geometry.left + self.board.size * self.geometry.cell_width + 28
        if height < required_height or width < required_width:
            self._safe_addstr(0, 0, f"Terminal too small. Need at least {required_width}x{required_height}.")
            self.stdscr.refresh()
            return

        self._safe_addstr(0, 0, "Gomoku-AI TUI")
        self._safe_addstr(1, 0, self.message)
        self._safe_addstr(
            2,
            0,
            f"Mode: {self.mode} | Turn: {STONE_NAMES[self.current]} | Moves: {self.board.move_count}",
        )
        self._draw_board()
        self._safe_addstr(self.geometry.top + self.board.size + 3, 0, "Controls: arrows/HJKL move | Space/Enter place | mouse click place | q quit")
        self.stdscr.refresh()

    def _draw_board(self) -> None:
        for col in range(self.board.size):
            label = _column_label(col)
            _y, x = board_to_screen(0, col, self.geometry)
            self._safe_addstr(self.geometry.top, x, label[-2:].rjust(2))

        for row in range(self.board.size):
            y, _x = board_to_screen(row, 0, self.geometry)
            self._safe_addstr(y, 0, f"{row + 1:>2}")
            for col in range(self.board.size):
                cell_y, cell_x = board_to_screen(row, col, self.geometry)
                stone = self.board.grid[row][col]
                label = STONE_LABELS[stone]
                if self.board.last_move == (row, col) and stone != EMPTY:
                    label = label.lower()
                attr = curses.A_REVERSE if self.cursor == (row, col) else curses.A_NORMAL
                self._safe_addstr(cell_y, cell_x, label.rjust(2), attr)

    def _safe_addstr(self, y: int, x: int, text: str, attr: int = curses.A_NORMAL) -> None:
        try:
            self.stdscr.addstr(y, x, text, attr)
        except curses.error:
            pass


def _format_move(row: int, col: int) -> str:
    return format_move(row, col)


def _column_label(index: int) -> str:
    return column_label(index)


def _clamp_depth(depth: int) -> int:
    return min(max(depth, MIN_UI_DEPTH), MAX_UI_DEPTH)
