from gomoku_ai.core import BLACK
from gomoku_ai.evaluate import (
    DEFAULT_EVALUATION_GAMES,
    DEFAULT_EVALUATION_JOBS,
    ComparisonSummary,
    MatchRecord,
    build_parser,
    compare_players,
    format_summary,
    play_match,
)
from gomoku_ai.players import PlayerSpec


def test_play_match_records_stopped_match():
    record = play_match(
        PlayerSpec("v0", seed=1),
        PlayerSpec("v0", seed=2),
        size=5,
        max_moves=1,
    )

    assert record.black_label == "random:v0"
    assert record.white_label == "random:v0"
    assert record.moves == 1
    assert record.stopped


def test_compare_players_can_alternate_colors():
    first = PlayerSpec("v2", depth=1)
    second = PlayerSpec("v0")

    summary = compare_players(first, second, games=2, size=5, max_moves=1)

    assert summary.records[0].black_label == "alpha-beta:v2(d1)"
    assert summary.records[1].black_label == "random:v0"
    assert len(summary.records) == 2


def test_format_summary_includes_records():
    summary = compare_players(
        PlayerSpec("v0", seed=1),
        PlayerSpec("v0", seed=2),
        games=1,
        size=5,
        max_moves=1,
    )

    text = format_summary(summary)

    assert "Comparison: random:v0 vs random:v0" in text
    assert "Games: 1" in text
    assert "Games detail:" in text


def test_summary_counts_roles_when_labels_match():
    spec = PlayerSpec("v0")
    summary = ComparisonSummary(
        first=spec,
        second=spec,
        records=(
            MatchRecord(
                black=spec,
                white=spec,
                winner=BLACK,
                moves=5,
                black_role="first",
                white_role="second",
            ),
        ),
    )

    assert summary.first_wins == 1
    assert summary.second_wins == 0


def test_parser_defaults_to_eight_games_for_formal_comparison():
    args = build_parser().parse_args([])

    assert DEFAULT_EVALUATION_GAMES == 8
    assert args.games == 8
    assert args.first_depth == 5
    assert args.second_depth == 5
    assert DEFAULT_EVALUATION_JOBS == 0
    assert args.jobs == 0


def test_compare_players_can_run_games_in_parallel():
    summary = compare_players(
        PlayerSpec("v0", seed=1),
        PlayerSpec("v0", seed=2),
        games=2,
        size=5,
        max_moves=1,
        jobs=2,
    )

    assert len(summary.records) == 2
    assert [record.moves for record in summary.records] == [1, 1]
