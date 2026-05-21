from __future__ import annotations

import argparse
from dataclasses import dataclass, replace

from gomoku_ai.core import BLACK, DRAW, WHITE, Board, STONE_NAMES, opponent
from gomoku_ai.players import ALGORITHM_NAMES, REGISTRY_NAME_CHOICES, PlayerSpec, create_player, resolve_algorithm_version


@dataclass(frozen=True)
class MatchRecord:
    black: PlayerSpec
    white: PlayerSpec
    winner: int | None
    moves: int
    stopped: bool = False
    black_role: str | None = None
    white_role: str | None = None

    @property
    def black_label(self) -> str:
        return self.black.label

    @property
    def white_label(self) -> str:
        return self.white.label

    @property
    def winner_label(self) -> str:
        if self.winner == BLACK:
            return self.black_label
        if self.winner == WHITE:
            return self.white_label
        if self.winner == DRAW:
            return "draw"
        return "stopped"

    @property
    def winner_role(self) -> str | None:
        if self.winner == BLACK:
            return self.black_role
        if self.winner == WHITE:
            return self.white_role
        return None


@dataclass(frozen=True)
class ComparisonSummary:
    first: PlayerSpec
    second: PlayerSpec
    records: tuple[MatchRecord, ...]

    @property
    def first_wins(self) -> int:
        return sum(1 for record in self.records if record.winner_role == "first")

    @property
    def second_wins(self) -> int:
        return sum(1 for record in self.records if record.winner_role == "second")

    @property
    def draws(self) -> int:
        return sum(1 for record in self.records if record.winner == DRAW)

    @property
    def stopped(self) -> int:
        return sum(1 for record in self.records if record.stopped)

    @property
    def average_moves(self) -> float:
        if not self.records:
            return 0.0
        return sum(record.moves for record in self.records) / len(self.records)


def play_match(
    black: PlayerSpec,
    white: PlayerSpec,
    *,
    size: int = 15,
    max_moves: int | None = None,
    black_role: str | None = None,
    white_role: str | None = None,
) -> MatchRecord:
    board = Board(size=size)
    players = {
        BLACK: create_player(BLACK, black),
        WHITE: create_player(WHITE, white),
    }
    current = BLACK
    winner: int | None = None
    stopped = False

    while True:
        if max_moves is not None and board.move_count >= max_moves:
            stopped = True
            break

        row, col = players[current].choose_move(board)
        board.play(row, col, current)
        result = board.winner_from(row, col)
        if result is not None:
            winner = result
            break

        current = opponent(current)

    return MatchRecord(
        black=black,
        white=white,
        winner=winner,
        moves=board.move_count,
        stopped=stopped,
        black_role=black_role,
        white_role=white_role,
    )


def compare_players(
    first: PlayerSpec,
    second: PlayerSpec,
    *,
    games: int = 10,
    size: int = 15,
    max_moves: int | None = None,
    alternate_colors: bool = True,
) -> ComparisonSummary:
    if games < 1:
        raise ValueError("games must be at least 1")

    records: list[MatchRecord] = []
    for index in range(games):
        seeded_first = replace(first, seed=first.seed + index * 2)
        seeded_second = replace(second, seed=second.seed + index * 2 + 1)

        if alternate_colors and index % 2 == 1:
            black = seeded_second
            white = seeded_first
            black_role = "second"
            white_role = "first"
        else:
            black = seeded_first
            white = seeded_second
            black_role = "first"
            white_role = "second"

        records.append(
            play_match(
                black,
                white,
                size=size,
                max_moves=max_moves,
                black_role=black_role,
                white_role=white_role,
            )
        )

    return ComparisonSummary(first=first, second=second, records=tuple(records))


def format_summary(summary: ComparisonSummary) -> str:
    lines = [
        f"Comparison: {summary.first.label} vs {summary.second.label}",
        f"Games: {len(summary.records)}",
        f"{summary.first.label} wins: {summary.first_wins}",
        f"{summary.second.label} wins: {summary.second_wins}",
        f"Draws: {summary.draws}",
        f"Stopped: {summary.stopped}",
        f"Average moves: {summary.average_moves:.1f}",
        "",
        "Games detail:",
    ]
    for index, record in enumerate(summary.records, start=1):
        winner = record.winner_label
        if record.winner in (BLACK, WHITE):
            winner = f"{winner} as {STONE_NAMES[record.winner]}"
        lines.append(
            f"{index}. black={record.black_label}, white={record.white_label}, "
            f"winner={winner}, moves={record.moves}"
        )
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Compare Gomoku AI algorithms head to head.")
    parser.add_argument("--first", default="alpha-beta", help=f"First AI registry name, one of {', '.join(REGISTRY_NAME_CHOICES)}.")
    parser.add_argument("--first-version", choices=ALGORITHM_NAMES)
    parser.add_argument("--second", default="random", help=f"Second AI registry name, one of {', '.join(REGISTRY_NAME_CHOICES)}.")
    parser.add_argument("--second-version", choices=ALGORITHM_NAMES)
    parser.add_argument("--first-depth", type=int, default=4)
    parser.add_argument("--second-depth", type=int, default=1)
    parser.add_argument("--games", type=int, default=10)
    parser.add_argument("--size", type=int, default=15)
    parser.add_argument("--max-moves", type=int)
    parser.add_argument("--no-alternate-colors", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> ComparisonSummary:
    args = build_parser().parse_args(argv)
    summary = compare_players(
        PlayerSpec(resolve_algorithm_version(args.first, args.first_version), depth=args.first_depth),
        PlayerSpec(resolve_algorithm_version(args.second, args.second_version), depth=args.second_depth),
        games=args.games,
        size=args.size,
        max_moves=args.max_moves,
        alternate_colors=not args.no_alternate_colors,
    )
    print(format_summary(summary))
    return summary


def run() -> None:
    main()


if __name__ == "__main__":
    run()
