from gomoku_ai.cli import build_parser, main, normalize_algorithm_args, play_ai_ai, play_human_ai
from gomoku_ai.core import BLACK


def _silent(*_args, **_kwargs):
    return None


def test_ai_ai_loop_can_stop_after_max_moves():
    result = play_ai_ai(
        size=5,
        black_depth=1,
        white_depth=1,
        max_moves=2,
        output_func=_silent,
    )

    assert result.moves == 2
    assert result.winner is None


def test_human_ai_loop_accepts_mocked_input():
    moves = iter(["A1"])

    result = play_human_ai(
        size=5,
        human_stone=BLACK,
        depth=1,
        max_moves=2,
        input_func=lambda _prompt: next(moves),
        output_func=_silent,
    )

    assert result.moves == 2


def test_main_ai_ai_smoke():
    result = main(["--mode", "ai-ai", "--size", "5", "--depth", "1", "--max-moves", "1"])

    assert result.moves == 1


def test_main_ai_ai_accepts_algorithm_options():
    result = main(
        [
            "--mode",
            "ai-ai",
            "--size",
            "5",
            "--black-ai",
            "v1",
            "--white-ai",
            "v0",
            "--max-moves",
            "1",
        ]
    )

    assert result.moves == 1


def test_tui_shortcut_sets_ui_mode():
    args = build_parser().parse_args(["--tui", "--mode", "human-ai"])

    assert args.ui == "tui"


def test_default_depth_is_four():
    args = normalize_algorithm_args(build_parser().parse_args(["--mode", "human-ai"]))

    assert args.depth == 4
    assert args.ai == "v4"


def test_algorithm_options_are_available():
    args = build_parser().parse_args(
        [
            "--mode",
            "ai-ai",
            "--ai",
            "alpha-beta",
            "--ai-version",
            "v3",
            "--black-ai",
            "alpha-beta",
            "--black-version",
            "v2",
            "--white-ai",
            "alpha-beta",
            "--white-version",
            "v1",
        ]
    )
    args = normalize_algorithm_args(args)

    assert args.ai == "v3"
    assert args.black_ai == "v2"
    assert args.white_ai == "v1"


def test_legacy_algorithm_options_are_normalized():
    args = normalize_algorithm_args(
        build_parser().parse_args(
            [
                "--mode",
                "ai-ai",
                "--ai",
                "random",
                "--black-ai",
                "alphabeta-v3",
                "--white-ai",
                "alphabeta-v1",
            ]
        )
    )

    assert args.ai == "v0"
    assert args.black_ai == "v3"
    assert args.white_ai == "v1"


def test_version_options_can_override_shared_registry():
    args = normalize_algorithm_args(
        build_parser().parse_args(
            [
                "--mode",
                "ai-ai",
                "--ai",
                "alpha-beta",
                "--black-version",
                "v1",
                "--white-version",
                "v3",
            ]
        )
    )

    assert args.ai == "v4"
    assert args.black_ai == "v1"
    assert args.white_ai == "v3"


def test_mismatched_registry_and_version_is_rejected():
    args = build_parser().parse_args(
        [
            "--mode",
            "ai-ai",
            "--ai",
            "random",
            "--ai-version",
            "v2",
        ]
    )

    try:
        normalize_algorithm_args(args)
    except ValueError as exc:
        assert "does not belong" in str(exc)
    else:
        raise AssertionError("expected mismatched registry/version to fail")


def test_gui_shortcut_sets_ui_mode():
    args = build_parser().parse_args(["--gui", "--mode", "human-ai"])

    assert args.ui == "gui"


def test_gui_ui_mode_is_available():
    args = build_parser().parse_args(["--ui", "gui", "--mode", "ai-ai"])

    assert args.ui == "gui"
