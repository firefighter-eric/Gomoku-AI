import pytest

from gomoku_ai.core import BLACK, DRAW, WHITE, Board, InvalidMoveError, parse_move


@pytest.mark.parametrize(
    "moves,last_move",
    [
        ([(7, col) for col in range(5)], (7, 4)),
        ([(row, 7) for row in range(5)], (4, 7)),
        ([(row, row) for row in range(5)], (4, 4)),
        ([(row, 4 - row) for row in range(5)], (4, 0)),
    ],
)
def test_five_in_any_direction_wins(moves, last_move):
    board = Board(size=15)
    for row, col in moves:
        board.play(row, col, BLACK)

    assert board.winner_from(*last_move) == BLACK


def test_overline_also_wins():
    board = Board(size=15)
    for col in range(6):
        board.play(7, col, WHITE)

    assert board.winner_from(7, 5) == WHITE


def test_illegal_moves_raise():
    board = Board(size=15)
    board.play(7, 7, BLACK)

    with pytest.raises(InvalidMoveError):
        board.play(7, 7, WHITE)
    with pytest.raises(InvalidMoveError):
        board.play(-1, 0, WHITE)
    with pytest.raises(ValueError):
        board.play(0, 0, 0)


def test_draw_detection_on_full_board_without_five():
    board = Board(size=3, win_length=3)
    values = [
        [BLACK, WHITE, BLACK],
        [BLACK, WHITE, WHITE],
        [WHITE, BLACK, BLACK],
    ]
    board = Board(size=3, win_length=3, grid=values, last_move=(2, 2))

    assert board.winner() == DRAW


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("H8", (7, 7)),
        ("h8", (7, 7)),
        ("8 8", (7, 7)),
        ("8 H", (7, 7)),
        ("H 8", (7, 7)),
    ],
)
def test_parse_move_formats(text, expected):
    assert parse_move(text, size=15) == expected


def test_render_marks_last_move_lowercase():
    board = Board(size=5)
    board.play(2, 2, BLACK)

    assert " x" in board.render()
