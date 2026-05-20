from gomoku_ai.ai import AlphaBetaAI, generate_candidate_moves, _move_wins
from gomoku_ai.core import BLACK, WHITE, Board


def test_candidate_moves_start_at_center():
    assert generate_candidate_moves(Board(size=15)) == [(7, 7)]


def test_candidate_moves_stay_near_existing_stones():
    board = Board(size=15)
    board.play(7, 7, BLACK)

    moves = generate_candidate_moves(board, radius=1)

    assert (6, 6) in moves
    assert (7, 7) not in moves
    assert (0, 0) not in moves


def test_ai_first_move_is_center():
    ai = AlphaBetaAI(BLACK, depth=2)

    assert ai.choose_move(Board(size=15)) == (7, 7)


def test_ai_finds_one_move_win():
    board = Board(size=15)
    for col in range(4):
        board.play(7, col + 3, BLACK)
    board.play(6, 6, WHITE)
    ai = AlphaBetaAI(BLACK, depth=2)

    assert ai.choose_move(board) in {(7, 2), (7, 7)}


def test_ai_blocks_one_move_win():
    board = Board(size=15)
    for col in range(4):
        board.play(7, col + 3, WHITE)
    board.play(6, 6, BLACK)
    ai = AlphaBetaAI(BLACK, depth=2)

    assert ai.choose_move(board) in {(7, 2), (7, 7)}


def test_fast_move_win_check_does_not_mutate_board():
    board = Board(size=15)
    for col in range(4):
        board.play(7, col + 3, BLACK)

    assert _move_wins(board, 7, 7, BLACK)
    assert board.grid[7][7] == 0
    assert board.move_count == 4


def test_deeper_search_uses_narrower_inner_candidate_limit():
    ai = AlphaBetaAI(BLACK, depth=4, candidate_limit=18)

    assert ai._candidate_limit_for_depth(3) == 18
    assert ai._candidate_limit_for_depth(2) == 14
    assert ai._candidate_limit_for_depth(1) == 10
