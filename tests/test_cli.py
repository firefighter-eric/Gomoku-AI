from gomoku_ai.cli import build_parser, main, play_ai_ai, play_human_ai
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


def test_tui_shortcut_sets_ui_mode():
    args = build_parser().parse_args(["--tui", "--mode", "human-ai"])

    assert args.ui == "tui"
