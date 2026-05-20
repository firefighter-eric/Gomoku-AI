from __future__ import annotations

import time
from dataclasses import dataclass, replace
from typing import Callable

from gomoku_ai.ai import AlphaBetaAI
from gomoku_ai.core import BLACK, DRAW, WHITE, Board, InvalidMoveError, STONE_NAMES, opponent

Clock = Callable[[], float]


@dataclass(frozen=True)
class GameSettings:
    mode: str = "human-ai"
    size: int = 15
    human_stone: int = BLACK
    depth: int = 4
    black_depth: int = 4
    white_depth: int = 4
    max_moves: int | None = None


@dataclass
class GameResult:
    winner: int | None
    moves: int
    elapsed: float
    resigned: bool = False


@dataclass(frozen=True)
class TurnOutcome:
    kind: str
    message: str
    move: tuple[int, int] | None = None
    stone: int | None = None
    result: GameResult | None = None

    @property
    def finished(self) -> bool:
        return self.result is not None

    @property
    def valid(self) -> bool:
        return self.kind != "invalid"


class GameSession:
    """Interface-neutral Gomoku game controller shared by CLI, TUI, and GUI."""

    def __init__(self, settings: GameSettings | None = None, *, clock: Clock = time.perf_counter) -> None:
        self.settings = settings or GameSettings()
        self._clock = clock
        self.board = Board(size=self.settings.size)
        self.current = BLACK
        self.started = self._clock()
        self.result: GameResult | None = None
        self.players = self._create_players()

    def restart(self, settings: GameSettings | None = None) -> None:
        if settings is not None:
            self.settings = settings
        self.board = Board(size=self.settings.size)
        self.current = BLACK
        self.started = self._clock()
        self.result = None
        self.players = self._create_players()

    def with_settings(self, **changes: object) -> GameSettings:
        return replace(self.settings, **changes)

    def is_ai_turn(self) -> bool:
        if self.result is not None:
            return False
        return self.settings.mode == "ai-ai" or self.current != self.settings.human_stone

    def play_human_move(self, row: int, col: int) -> TurnOutcome:
        if self.result is not None:
            return self._already_finished()
        if self._max_moves_reached():
            return self.stop()
        if self.is_ai_turn():
            return TurnOutcome(kind="invalid", message="It is not the human player's turn.")
        return self._place_current(row, col)

    def play_ai_move(self) -> TurnOutcome:
        if self.result is not None:
            return self._already_finished()
        if self._max_moves_reached():
            return self.stop()
        if not self.is_ai_turn():
            return TurnOutcome(kind="invalid", message="It is not an AI turn.")
        row, col = self.players[self.current].choose_move(self.board)
        return self._place_current(row, col)

    def stop(self) -> TurnOutcome:
        if self.result is not None:
            return self._already_finished()
        outcome = self._finish(None)
        return TurnOutcome(kind="stopped", message=outcome.message, result=outcome.result)

    def resign(self, winner: int | None = None) -> TurnOutcome:
        if self.result is not None:
            return self._already_finished()
        if winner is None and self.settings.mode == "human-ai":
            winner = opponent(self.settings.human_stone)
        return self._finish(winner, resigned=winner in (BLACK, WHITE))

    def finish(self, winner: int | None, *, resigned: bool = False) -> TurnOutcome:
        if self.result is not None:
            return self._already_finished()
        return self._finish(winner, resigned=resigned)

    def _create_players(self) -> dict[int, AlphaBetaAI]:
        if self.settings.mode == "ai-ai":
            return {
                BLACK: AlphaBetaAI(BLACK, depth=self.settings.black_depth),
                WHITE: AlphaBetaAI(WHITE, depth=self.settings.white_depth),
            }
        return {
            BLACK: AlphaBetaAI(BLACK, depth=self.settings.depth),
            WHITE: AlphaBetaAI(WHITE, depth=self.settings.depth),
        }

    def _place_current(self, row: int, col: int) -> TurnOutcome:
        stone = self.current
        try:
            self.board.play(row, col, stone)
        except InvalidMoveError as exc:
            return TurnOutcome(kind="invalid", message=f"Invalid move: {exc}", move=(row, col), stone=stone)

        result = self.board.winner_from(row, col)
        move_text = format_move(row, col)
        if result is not None:
            outcome = self._finish(result)
            return TurnOutcome(
                kind="finished",
                message=f"{STONE_NAMES[stone].capitalize()} played {move_text}.",
                move=(row, col),
                stone=stone,
                result=outcome.result,
            )

        if self._max_moves_reached():
            outcome = self._finish(None)
            return TurnOutcome(
                kind="stopped",
                message=f"Stopped after {self.board.move_count} moves.",
                move=(row, col),
                stone=stone,
                result=outcome.result,
            )

        self.current = opponent(self.current)
        return TurnOutcome(
            kind="played",
            message=f"{STONE_NAMES[stone].capitalize()} played {move_text}.",
            move=(row, col),
            stone=stone,
        )

    def _max_moves_reached(self) -> bool:
        return self.settings.max_moves is not None and self.board.move_count >= self.settings.max_moves

    def _finish(self, winner: int | None, *, resigned: bool = False) -> TurnOutcome:
        self.result = GameResult(
            winner=winner,
            moves=self.board.move_count,
            elapsed=self._clock() - self.started,
            resigned=resigned,
        )
        return TurnOutcome(kind="finished", message=result_message(self.result), result=self.result)

    def _already_finished(self) -> TurnOutcome:
        assert self.result is not None
        return TurnOutcome(kind="finished", message=result_message(self.result), result=self.result)


def format_move(row: int, col: int) -> str:
    return f"{column_label(col)}{row + 1}"


def column_label(index: int) -> str:
    value = index
    label = ""
    while True:
        label = chr(ord("A") + value % 26) + label
        value = value // 26 - 1
        if value < 0:
            return label


def result_message(result: GameResult) -> str:
    if result.resigned and result.winner in (BLACK, WHITE):
        return f"Resigned. {STONE_NAMES[result.winner].capitalize()} wins."
    if result.winner == DRAW:
        return f"Draw after {result.moves} moves."
    if result.winner in (BLACK, WHITE):
        return f"{STONE_NAMES[result.winner].capitalize()} wins after {result.moves} moves."
    return f"Stopped after {result.moves} moves."
