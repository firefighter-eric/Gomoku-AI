from __future__ import annotations

import argparse
import time
from dataclasses import dataclass
from typing import Callable

from gomoku_ai.ai import AlphaBetaAI
from gomoku_ai.core import BLACK, DRAW, WHITE, Board, InvalidMoveError, STONE_NAMES, opponent, parse_move

InputFunc = Callable[[str], str]
OutputFunc = Callable[..., None]


@dataclass
class GameResult:
    winner: int | None
    moves: int
    elapsed: float
    resigned: bool = False


def main(argv: list[str] | None = None) -> GameResult:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.mode is None:
        args = prompt_for_args(args)

    if args.ui == "tui":
        from gomoku_ai.tui import play_tui

        return play_tui(
            mode=args.mode,
            size=args.size,
            human_stone=_stone_from_name(args.human),
            depth=args.depth,
            black_depth=args.black_depth or args.depth,
            white_depth=args.white_depth or args.depth,
            delay=args.delay,
            max_moves=args.max_moves,
        )

    if args.mode == "human-ai":
        return play_human_ai(
            size=args.size,
            human_stone=_stone_from_name(args.human),
            depth=args.depth,
            max_moves=args.max_moves,
        )
    if args.mode == "ai-ai":
        return play_ai_ai(
            size=args.size,
            black_depth=args.black_depth or args.depth,
            white_depth=args.white_depth or args.depth,
            delay=args.delay,
            max_moves=args.max_moves,
        )
    raise ValueError(f"unknown mode: {args.mode}")


def run() -> None:
    main()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Play Gomoku against an alpha-beta AI.")
    parser.add_argument("--mode", choices=("human-ai", "ai-ai"))
    parser.add_argument("--ui", choices=("plain", "tui"), default="plain")
    parser.add_argument("--tui", action="store_const", const="tui", dest="ui", help="Shortcut for --ui tui.")
    parser.add_argument("--human", choices=("black", "white"), default="black")
    parser.add_argument("--depth", type=int, default=3)
    parser.add_argument("--black-depth", type=int)
    parser.add_argument("--white-depth", type=int)
    parser.add_argument("--size", type=int, default=15)
    parser.add_argument("--delay", type=float, default=0.0)
    parser.add_argument("--max-moves", type=int)
    return parser


def prompt_for_args(args: argparse.Namespace, input_func: InputFunc = input) -> argparse.Namespace:
    mode = input_func("Choose game mode (1: human-ai, 2: ai-ai): ").strip()
    args.mode = "ai-ai" if mode == "2" else "human-ai"

    if args.mode == "human-ai":
        side = input_func("Choose your side (black/white, default black): ").strip().lower()
        args.human = side if side in {"black", "white"} else "black"

    depth = input_func(f"Search depth (default {args.depth}): ").strip()
    if depth:
        args.depth = int(depth)

    return args


def play_human_ai(
    *,
    size: int = 15,
    human_stone: int = BLACK,
    depth: int = 3,
    max_moves: int | None = None,
    input_func: InputFunc = input,
    output_func: OutputFunc = print,
) -> GameResult:
    board = Board(size=size)
    ai_stone = opponent(human_stone)
    ai = AlphaBetaAI(ai_stone, depth=depth)
    current = BLACK
    started = time.perf_counter()

    output_func(board.render())
    while max_moves is None or board.move_count < max_moves:
        if current == human_stone:
            move = _prompt_human_move(board, current, input_func, output_func)
            if move is None:
                elapsed = time.perf_counter() - started
                return GameResult(winner=opponent(human_stone), moves=board.move_count, elapsed=elapsed, resigned=True)
        else:
            move = ai.choose_move(board)
            output_func(f"AI ({STONE_NAMES[current]}) plays {_format_move(*move)}")

        row, col = move
        board.play(row, col, current)
        output_func(board.render())

        result = board.winner_from(row, col)
        if result is not None:
            elapsed = time.perf_counter() - started
            _print_result(result, board.move_count, elapsed, output_func)
            return GameResult(winner=result, moves=board.move_count, elapsed=elapsed)

        current = opponent(current)

    elapsed = time.perf_counter() - started
    output_func(f"Stopped after {board.move_count} moves.")
    return GameResult(winner=None, moves=board.move_count, elapsed=elapsed)


def play_ai_ai(
    *,
    size: int = 15,
    black_depth: int = 3,
    white_depth: int = 3,
    delay: float = 0.0,
    max_moves: int | None = None,
    output_func: OutputFunc = print,
) -> GameResult:
    board = Board(size=size)
    players = {
        BLACK: AlphaBetaAI(BLACK, depth=black_depth),
        WHITE: AlphaBetaAI(WHITE, depth=white_depth),
    }
    current = BLACK
    started = time.perf_counter()

    output_func(board.render())
    while max_moves is None or board.move_count < max_moves:
        move = players[current].choose_move(board)
        row, col = move
        board.play(row, col, current)
        output_func(f"AI ({STONE_NAMES[current]}) plays {_format_move(row, col)}")
        output_func(board.render())

        result = board.winner_from(row, col)
        if result is not None:
            elapsed = time.perf_counter() - started
            _print_result(result, board.move_count, elapsed, output_func)
            return GameResult(winner=result, moves=board.move_count, elapsed=elapsed)

        if delay > 0:
            time.sleep(delay)
        current = opponent(current)

    elapsed = time.perf_counter() - started
    output_func(f"Stopped after {board.move_count} moves.")
    return GameResult(winner=None, moves=board.move_count, elapsed=elapsed)


def _prompt_human_move(
    board: Board,
    stone: int,
    input_func: InputFunc,
    output_func: OutputFunc,
) -> tuple[int, int] | None:
    while True:
        raw = input_func(f"Your move ({STONE_NAMES[stone]}, e.g. H8 or 8 8, q to quit): ")
        if raw.strip().lower() in {"q", "quit", "exit"}:
            return None
        try:
            row, col = parse_move(raw, board.size)
            if not board.is_empty_at(row, col):
                raise InvalidMoveError("point is already occupied")
            return row, col
        except (InvalidMoveError, ValueError) as exc:
            output_func(f"Invalid move: {exc}")


def _print_result(result: int, moves: int, elapsed: float, output_func: OutputFunc) -> None:
    if result == DRAW:
        output_func(f"Draw after {moves} moves. Time: {elapsed:.2f}s")
    else:
        output_func(f"{STONE_NAMES[result].capitalize()} wins after {moves} moves. Time: {elapsed:.2f}s")


def _format_move(row: int, col: int) -> str:
    return f"{chr(ord('A') + col)}{row + 1}"


def _stone_from_name(name: str) -> int:
    return BLACK if name == "black" else WHITE


if __name__ == "__main__":
    run()
