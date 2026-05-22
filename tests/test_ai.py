from gomoku_ai.ai import (
    DOUBLE_THREE,
    OPEN_FOUR,
    OPEN_THREE,
    AlphaBetaAI,
    AlphaBetaV1AI,
    AlphaBetaV3AI,
    AlphaBetaV4AI,
    find_immediate_win_by_simulation,
    generate_candidate_moves,
    _move_wins,
    _score_line,
    _score_line_v3,
    _score_line_v4,
    _v3_local_score_after_move,
    _v3_threats_after_move,
    _v4_threats_after_move,
)
from gomoku_ai.core import BLACK, EMPTY, WHITE, Board


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


def test_v1_uses_fixed_inner_candidate_limit():
    ai = AlphaBetaV1AI(BLACK, depth=4, candidate_limit=18)

    assert ai._candidate_limit_for_depth(3) == 18
    assert ai._candidate_limit_for_depth(2) == 18
    assert ai._candidate_limit_for_depth(1) == 18


def test_ai_resets_hash_state_when_board_size_changes():
    ai = AlphaBetaAI(BLACK, depth=1)
    small = Board(size=15)
    small.play(7, 7, WHITE)
    large = Board(size=19)
    large.play(18, 18, WHITE)

    ai.choose_move(small)

    assert large.is_empty_at(*ai.choose_move(large))


def test_v1_simulated_win_check_does_not_mutate_board():
    board = Board(size=15)
    for col in range(4):
        board.play(7, col + 3, BLACK)

    assert find_immediate_win_by_simulation(board, BLACK) in {(7, 2), (7, 7)}
    assert board.move_count == 4
    assert board.grid[7][2] == EMPTY
    assert board.grid[7][7] == EMPTY


def test_v1_orders_candidates_by_global_board_score():
    board = Board(size=15)
    for col in range(4):
        board.play(7, col + 3, BLACK)
    board.play(6, 6, WHITE)
    ai = AlphaBetaV1AI(BLACK, depth=2, candidate_limit=4)

    moves = ai._ordered_candidates(board, BLACK, limit=4)

    assert any(move in moves for move in {(7, 2), (7, 7)})


def test_v3_line_scoring_recognizes_open_four_and_open_three():
    open_four = [EMPTY, BLACK, BLACK, BLACK, BLACK, EMPTY]
    open_three = [EMPTY, EMPTY, BLACK, BLACK, BLACK, EMPTY]

    assert _score_line_v3(open_four, BLACK) >= OPEN_FOUR
    assert _score_line_v3(open_four, BLACK) > _score_line(open_four, BLACK)
    assert _score_line_v3(open_three, BLACK) >= OPEN_THREE


def test_v4_line_scoring_matches_v3_patterns():
    open_four = [EMPTY, BLACK, BLACK, BLACK, BLACK, EMPTY]
    open_three = [EMPTY, EMPTY, BLACK, BLACK, BLACK, EMPTY]

    assert _score_line_v4(open_four, BLACK) == _score_line_v3(open_four, BLACK)
    assert _score_line_v4(open_three, BLACK) == _score_line_v3(open_three, BLACK)


def test_v3_candidate_limit_preserves_tactical_moves():
    board = Board(size=15)
    for col in range(3, 7):
        board.play(5, col, BLACK)
        board.play(9, col, WHITE)
    ai = AlphaBetaV3AI(BLACK, depth=2, candidate_limit=1)

    moves = ai._ordered_candidates(board, BLACK, limit=1)

    assert any(move in moves for move in {(5, 2), (5, 7)})
    assert any(move in moves for move in {(9, 2), (9, 7)})


def test_v3_scores_double_three_as_explicit_threat():
    board = Board(size=15)
    for col in (8, 9):
        board.play(7, col, BLACK)
    for row in (8, 9):
        board.play(row, 7, BLACK)

    threats = _v3_threats_after_move(board, 7, 7, BLACK)

    assert threats.has_double_three
    assert _v3_local_score_after_move(board, 7, 7, BLACK) >= DOUBLE_THREE


def test_v3_candidate_limit_preserves_defensive_double_three():
    board = Board(size=15)
    for col in (8, 9):
        board.play(7, col, WHITE)
    for row in (8, 9):
        board.play(row, 7, WHITE)
    for col in range(3, 7):
        board.play(5, col, BLACK)
    ai = AlphaBetaV3AI(BLACK, depth=2, candidate_limit=1)

    moves = ai._ordered_candidates(board, BLACK, limit=1)

    assert any(move in moves for move in {(5, 2), (5, 7)})
    assert (7, 7) in moves


def test_v4_keeps_v3_tactical_candidate_guards():
    board = Board(size=15)
    for col in (8, 9):
        board.play(7, col, WHITE)
    for row in (8, 9):
        board.play(row, 7, WHITE)
    for col in range(3, 7):
        board.play(5, col, BLACK)
    ai = AlphaBetaV4AI(BLACK, depth=2, candidate_limit=1)

    moves = ai._ordered_candidates(board, BLACK, limit=1)

    assert any(move in moves for move in {(5, 2), (5, 7)})
    assert (7, 7) in moves
    assert _v4_threats_after_move(board, 7, 7, WHITE).has_double_three
