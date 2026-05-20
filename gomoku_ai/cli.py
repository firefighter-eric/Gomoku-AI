from __future__ import annotations

import argparse
import time
from typing import Callable

from gomoku_ai.core import BLACK, DRAW, WHITE, Board, InvalidMoveError, STONE_NAMES, parse_move
from gomoku_ai.game import GameResult, GameSession, GameSettings, format_move

InputFunc = Callable[[str], str]
OutputFunc = Callable[..., None]


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
    if args.ui == "gui":
        from gomoku_ai.gui import play_gui

        return play_gui(
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
    parser.add_argument("--ui", choices=("plain", "tui", "gui"), default="plain")
    parser.add_argument("--tui", action="store_const", const="tui", dest="ui", help="Shortcut for --ui tui.")
    parser.add_argument("--gui", action="store_const", const="gui", dest="ui", help="Shortcut for --ui gui.")
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
    session = GameSession(
        GameSettings(
            mode="human-ai",
            size=size,
            human_stone=human_stone,
            depth=depth,
            black_depth=depth,
            white_depth=depth,
            max_moves=max_moves,
        )
    )

    output_func(session.board.render())
    while session.result is None:
        if not session.is_ai_turn():
            move = _prompt_human_move(session.board, session.current, input_func, output_func)
            if move is None:
                outcome = session.resign()
                assert outcome.result is not None
                return outcome.result
            outcome = session.play_human_move(*move)
        else:
            stone = session.current
            outcome = session.play_ai_move()
            if outcome.move is not None:
                output_func(f"AI ({STONE_NAMES[stone]}) plays {_format_move(*outcome.move)}")

        if outcome.move is not None and outcome.valid:
            output_func(session.board.render())
        elif not outcome.valid:
            output_func(outcome.message)

        if outcome.result is not None:
            _print_result(outcome.result, output_func)
            return outcome.result

    assert session.result is not None
    return session.result


def play_ai_ai(
    *,
    size: int = 15,
    black_depth: int = 3,
    white_depth: int = 3,
    delay: float = 0.0,
    max_moves: int | None = None,
    output_func: OutputFunc = print,
) -> GameResult:
    session = GameSession(
        GameSettings(
            mode="ai-ai",
            size=size,
            black_depth=black_depth,
            white_depth=white_depth,
            max_moves=max_moves,
        )
    )

    output_func(session.board.render())
    while session.result is None:
        stone = session.current
        outcome = session.play_ai_move()
        if outcome.move is not None:
            output_func(f"AI ({STONE_NAMES[stone]}) plays {_format_move(*outcome.move)}")
            output_func(session.board.render())
        elif not outcome.valid:
            output_func(outcome.message)

        if outcome.result is not None:
            _print_result(outcome.result, output_func)
            return outcome.result

        if delay > 0:
            time.sleep(delay)

    assert session.result is not None
    return session.result


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


def _print_result(result: GameResult, output_func: OutputFunc) -> None:
    if result.winner == DRAW:
        output_func(f"Draw after {result.moves} moves. Time: {result.elapsed:.2f}s")
    elif result.winner in (BLACK, WHITE):
        output_func(f"{STONE_NAMES[result.winner].capitalize()} wins after {result.moves} moves. Time: {result.elapsed:.2f}s")
    else:
        output_func(f"Stopped after {result.moves} moves.")


def _format_move(row: int, col: int) -> str:
    return format_move(row, col)


def _stone_from_name(name: str) -> int:
    return BLACK if name == "black" else WHITE


if __name__ == "__main__":
    run()
