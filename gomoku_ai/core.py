from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

EMPTY = 0
BLACK = 1
WHITE = -1
DRAW = 2

STONE_LABELS = {
    EMPTY: ".",
    BLACK: "X",
    WHITE: "O",
}

STONE_NAMES = {
    BLACK: "black",
    WHITE: "white",
    DRAW: "draw",
    EMPTY: "empty",
}


class InvalidMoveError(ValueError):
    """Raised when a move is outside the board or lands on an occupied point."""


@dataclass(frozen=True)
class Move:
    row: int
    col: int


@dataclass(frozen=True)
class MoveUndo:
    row: int
    col: int
    stone: int
    previous_last_move: tuple[int, int] | None


class Board:
    """Mutable Gomoku board using zero-based row and column indexes."""

    def __init__(
        self,
        size: int = 15,
        win_length: int = 5,
        grid: Iterable[Iterable[int]] | None = None,
        last_move: tuple[int, int] | None = None,
    ) -> None:
        if size < 1:
            raise ValueError("board size must be positive")
        if win_length < 1:
            raise ValueError("win_length must be positive")
        if size < win_length:
            raise ValueError("board size must be at least win_length")

        self.size = size
        self.win_length = win_length
        self.last_move = last_move

        if grid is None:
            self.grid = [[EMPTY for _ in range(size)] for _ in range(size)]
        else:
            rows = [list(row) for row in grid]
            if len(rows) != size or any(len(row) != size for row in rows):
                raise ValueError("grid dimensions must match board size")
            for row in rows:
                for value in row:
                    _validate_stone(value, allow_empty=True)
            self.grid = rows

    @property
    def move_count(self) -> int:
        return sum(1 for row in self.grid for value in row if value != EMPTY)

    def copy(self) -> Board:
        return Board(
            size=self.size,
            win_length=self.win_length,
            grid=[row[:] for row in self.grid],
            last_move=self.last_move,
        )

    def play(self, row: int, col: int, stone: int) -> Board:
        """Place a stone, mutate the board, and return self."""

        _validate_stone(stone, allow_empty=False)
        if not self.is_on_board(row, col):
            raise InvalidMoveError(f"move is outside the board: ({row}, {col})")
        if self.grid[row][col] != EMPTY:
            raise InvalidMoveError(f"point is already occupied: ({row}, {col})")

        self.grid[row][col] = stone
        self.last_move = (row, col)
        return self

    def with_move(self, row: int, col: int, stone: int) -> Board:
        board = self.copy()
        board.play(row, col, stone)
        return board

    def make_move(self, row: int, col: int, stone: int) -> MoveUndo:
        """Place a stone and return the data needed to undo it."""

        previous_last_move = self.last_move
        self.play(row, col, stone)
        return MoveUndo(
            row=row,
            col=col,
            stone=stone,
            previous_last_move=previous_last_move,
        )

    def undo_move(self, undo: MoveUndo) -> Board:
        """Undo the most recent move produced by make_move."""

        if not self.is_on_board(undo.row, undo.col):
            raise InvalidMoveError(f"move is outside the board: ({undo.row}, {undo.col})")
        if self.last_move != (undo.row, undo.col):
            raise InvalidMoveError("can only undo the most recent move")
        if self.grid[undo.row][undo.col] != undo.stone:
            raise InvalidMoveError(
                f"point does not contain the expected stone: ({undo.row}, {undo.col})"
            )

        self.grid[undo.row][undo.col] = EMPTY
        self.last_move = undo.previous_last_move
        return self

    def is_on_board(self, row: int, col: int) -> bool:
        return 0 <= row < self.size and 0 <= col < self.size

    def is_empty_at(self, row: int, col: int) -> bool:
        return self.is_on_board(row, col) and self.grid[row][col] == EMPTY

    def is_empty(self) -> bool:
        return self.move_count == 0

    def is_full(self) -> bool:
        return self.move_count == self.size * self.size

    def legal_moves(self) -> list[tuple[int, int]]:
        return [
            (row, col)
            for row in range(self.size)
            for col in range(self.size)
            if self.grid[row][col] == EMPTY
        ]

    def stones(self) -> Iterable[tuple[int, int, int]]:
        for row in range(self.size):
            for col in range(self.size):
                stone = self.grid[row][col]
                if stone != EMPTY:
                    yield row, col, stone

    def winner_from(self, row: int, col: int) -> int | None:
        if not self.is_on_board(row, col):
            raise InvalidMoveError(f"move is outside the board: ({row}, {col})")

        stone = self.grid[row][col]
        if stone == EMPTY:
            return DRAW if self.is_full() else None

        for row_step, col_step in ((0, 1), (1, 0), (1, 1), (1, -1)):
            total = 1
            total += self._count_direction(row, col, row_step, col_step, stone)
            total += self._count_direction(row, col, -row_step, -col_step, stone)
            if total >= self.win_length:
                return stone

        return DRAW if self.is_full() else None

    def winner(self) -> int | None:
        if self.last_move is not None:
            result = self.winner_from(*self.last_move)
            if result is not None:
                return result

        for row, col, _stone in self.stones():
            result = self.winner_from(row, col)
            if result in (BLACK, WHITE):
                return result

        return DRAW if self.is_full() else None

    def render(self, last_move: tuple[int, int] | None = None) -> str:
        marker = self.last_move if last_move is None else last_move
        columns = _column_labels(self.size)
        lines = ["    " + " ".join(f"{label:>2}" for label in columns)]

        for row_index, row in enumerate(self.grid):
            cells = []
            for col_index, stone in enumerate(row):
                label = STONE_LABELS[stone]
                if marker == (row_index, col_index) and stone != EMPTY:
                    label = label.lower()
                cells.append(f"{label:>2}")
            lines.append(f"{row_index + 1:>2}  " + " ".join(cells))

        return "\n".join(lines)

    def _count_direction(
        self,
        row: int,
        col: int,
        row_step: int,
        col_step: int,
        stone: int,
    ) -> int:
        count = 0
        row += row_step
        col += col_step
        while self.is_on_board(row, col) and self.grid[row][col] == stone:
            count += 1
            row += row_step
            col += col_step
        return count


def opponent(stone: int) -> int:
    _validate_stone(stone, allow_empty=False)
    return BLACK if stone == WHITE else WHITE


def parse_move(text: str, size: int = 15) -> tuple[int, int]:
    """Parse moves like H8, h8, or '8 8' into zero-based coordinates."""

    value = text.strip().upper()
    if not value:
        raise ValueError("empty move")

    normalized = value.replace(",", " ").replace(";", " ")
    parts = normalized.split()
    if len(parts) == 2 and all(part.isdigit() for part in parts):
        row = int(parts[0]) - 1
        col = int(parts[1]) - 1
        _validate_coordinate(row, col, size)
        return row, col

    if len(parts) == 2 and parts[0].isalpha() and parts[1].isdigit():
        col = _column_to_index(parts[0], size)
        row = int(parts[1]) - 1
        _validate_coordinate(row, col, size)
        return row, col

    if len(parts) == 2 and parts[0].isdigit() and parts[1].isalpha():
        row = int(parts[0]) - 1
        col = _column_to_index(parts[1], size)
        _validate_coordinate(row, col, size)
        return row, col

    letters = "".join(ch for ch in value if ch.isalpha())
    digits = "".join(ch for ch in value if ch.isdigit())
    if letters and digits and len(letters) + len(digits) == len(value):
        col = _column_to_index(letters, size)
        row = int(digits) - 1
        _validate_coordinate(row, col, size)
        return row, col

    raise ValueError(f"could not parse move: {text!r}")


def _validate_stone(stone: int, *, allow_empty: bool) -> None:
    valid = {BLACK, WHITE}
    if allow_empty:
        valid.add(EMPTY)
    if stone not in valid:
        raise ValueError(f"invalid stone: {stone!r}")


def _validate_coordinate(row: int, col: int, size: int) -> None:
    if not (0 <= row < size and 0 <= col < size):
        raise ValueError(f"move is outside the board: ({row + 1}, {col + 1})")


def _column_to_index(label: str, size: int) -> int:
    labels = _column_labels(size)
    if label not in labels:
        raise ValueError(f"unknown column: {label}")
    return labels.index(label)


def _column_labels(size: int) -> list[str]:
    labels = []
    for index in range(size):
        value = index
        label = ""
        while True:
            label = chr(ord("A") + value % 26) + label
            value = value // 26 - 1
            if value < 0:
                break
        labels.append(label)
    return labels
