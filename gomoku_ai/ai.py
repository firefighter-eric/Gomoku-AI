from __future__ import annotations

import random
from dataclasses import dataclass
from math import inf

from gomoku_ai.core import BLACK, DRAW, EMPTY, WHITE, Board, opponent

WIN_SCORE = 10_000_000
OPEN_FOUR = 1_000_000
FOUR = 100_000
OPEN_THREE = 12_000
THREE = 1_500
OPEN_TWO = 350
TWO = 80
SINGLE = 8
DIRECTIONS = ((0, 1), (1, 0), (1, 1), (1, -1))


@dataclass
class SearchStats:
    nodes: int = 0
    cache_hits: int = 0


class ZobristHasher:
    def __init__(self, size: int, seed: int = 20260521) -> None:
        rng = random.Random(seed + size)
        self.black = [[rng.getrandbits(64) for _ in range(size)] for _ in range(size)]
        self.white = [[rng.getrandbits(64) for _ in range(size)] for _ in range(size)]

    def hash_board(self, board: Board) -> int:
        value = 0
        for row, col, stone in board.stones():
            if stone == BLACK:
                value ^= self.black[row][col]
            elif stone == WHITE:
                value ^= self.white[row][col]
        return value


class AlphaBetaAI:
    """Alpha-beta Gomoku AI with heuristic move ordering and Zobrist caches."""

    name = "v2"

    def __init__(
        self,
        stone: int,
        depth: int = 4,
        candidate_radius: int = 2,
        candidate_limit: int = 18,
        seed: int = 20260521,
    ) -> None:
        if stone not in (BLACK, WHITE):
            raise ValueError("AI stone must be BLACK or WHITE")
        if depth < 1:
            raise ValueError("depth must be at least 1")

        self.stone = stone
        self.depth = depth
        self.candidate_radius = candidate_radius
        self.candidate_limit = candidate_limit
        self.seed = seed
        self._hasher: ZobristHasher | None = None
        self._hash_size: int | None = None
        self._eval_cache: dict[int, int] = {}
        self._search_cache: dict[tuple[int, int, int], int] = {}
        self.stats = SearchStats()

    def choose_move(self, board: Board) -> tuple[int, int]:
        if board.is_empty():
            center = board.size // 2
            return center, center

        winning_move = find_immediate_win(board, self.stone, self.candidate_radius)
        if winning_move is not None:
            return winning_move

        blocking_move = find_immediate_win(board, opponent(self.stone), self.candidate_radius)
        if blocking_move is not None:
            return blocking_move

        self._ensure_hasher(board.size)
        self.stats = SearchStats()
        candidates = self._ordered_candidates(board, self.stone, limit=self.candidate_limit)
        best_move = candidates[0]
        best_value = -inf
        alpha = -inf
        beta = inf

        for row, col in candidates:
            next_board = board.with_move(row, col, self.stone)
            value = self._alpha_beta(
                next_board,
                depth=self.depth - 1,
                alpha=alpha,
                beta=beta,
                current_stone=opponent(self.stone),
                last_move=(row, col),
            )
            if value > best_value:
                best_value = value
                best_move = (row, col)
            alpha = max(alpha, best_value)

        return best_move

    def _alpha_beta(
        self,
        board: Board,
        depth: int,
        alpha: float,
        beta: float,
        current_stone: int,
        last_move: tuple[int, int] | None,
    ) -> int:
        self.stats.nodes += 1

        terminal = board.winner_from(*last_move) if last_move is not None else board.winner()
        if terminal == self.stone:
            return WIN_SCORE + depth
        if terminal == opponent(self.stone):
            return -WIN_SCORE - depth
        if terminal == DRAW:
            return 0
        if depth <= 0:
            return self._evaluate(board)

        key = (self._hash(board), depth, current_stone)
        if key in self._search_cache:
            self.stats.cache_hits += 1
            return self._search_cache[key]

        maximizing = current_stone == self.stone
        candidates = self._ordered_candidates(
            board,
            current_stone,
            limit=self._candidate_limit_for_depth(depth),
        )
        cutoff = False

        if maximizing:
            value = -inf
            for row, col in candidates:
                child = board.with_move(row, col, current_stone)
                value = max(
                    value,
                    self._alpha_beta(
                        child,
                        depth - 1,
                        alpha,
                        beta,
                        opponent(current_stone),
                        (row, col),
                    ),
                )
                alpha = max(alpha, value)
                if beta <= alpha:
                    cutoff = True
                    break
        else:
            value = inf
            for row, col in candidates:
                child = board.with_move(row, col, current_stone)
                value = min(
                    value,
                    self._alpha_beta(
                        child,
                        depth - 1,
                        alpha,
                        beta,
                        opponent(current_stone),
                        (row, col),
                    ),
                )
                beta = min(beta, value)
                if beta <= alpha:
                    cutoff = True
                    break

        result = int(value)
        if not cutoff:
            self._search_cache[key] = result
        return result

    def _ordered_candidates(
        self,
        board: Board,
        stone: int,
        *,
        limit: int | None,
    ) -> list[tuple[int, int]]:
        candidates = generate_candidate_moves(board, radius=self.candidate_radius)
        scored = [
            (self._move_order_score(board, row, col, stone), row, col)
            for row, col in candidates
        ]
        scored.sort(reverse=True)
        if limit is not None and len(scored) > limit:
            scored = scored[:limit]
        return [(row, col) for _score, row, col in scored]

    def _move_order_score(self, board: Board, row: int, col: int, stone: int) -> int:
        center = (board.size - 1) / 2
        center_bonus = int((board.size - abs(center - row) - abs(center - col)) * 10)

        if _move_wins(board, row, col, stone):
            return WIN_SCORE
        if _move_wins(board, row, col, opponent(stone)):
            return WIN_SCORE // 2

        own_score = _local_score_after_move(board, row, col, stone)
        blocking_score = _local_score_after_move(board, row, col, opponent(stone))
        neighbor_bonus = _neighbor_count(board, row, col) * 20
        return own_score * 2 + int(blocking_score * 1.35) + center_bonus + neighbor_bonus

    def _candidate_limit_for_depth(self, depth: int) -> int:
        if self.depth <= 2:
            return self.candidate_limit
        if depth <= 1:
            return min(self.candidate_limit, 10)
        if depth <= 2:
            return min(self.candidate_limit, 14)
        return self.candidate_limit

    def _evaluate(self, board: Board) -> int:
        key = self._hash(board)
        if key in self._eval_cache:
            self.stats.cache_hits += 1
            return self._eval_cache[key]

        own = _evaluate_for(board, self.stone)
        enemy = _evaluate_for(board, opponent(self.stone))
        score = own - int(enemy * 1.12) + _center_bias(board, self.stone)
        self._eval_cache[key] = score
        return score

    def _ensure_hasher(self, size: int) -> None:
        if self._hasher is None or self._hash_size != size:
            self._hasher = ZobristHasher(size, self.seed)
            self._hash_size = size
            self._eval_cache.clear()
            self._search_cache.clear()

    def _hash(self, board: Board) -> int:
        self._ensure_hasher(board.size)
        assert self._hasher is not None
        return self._hasher.hash_board(board)


class AlphaBetaV1AI(AlphaBetaAI):
    """Historical alpha-beta variant kept for algorithm comparison."""

    name = "v1"

    def choose_move(self, board: Board) -> tuple[int, int]:
        if board.is_empty():
            center = board.size // 2
            return center, center

        winning_move = find_immediate_win_by_simulation(board, self.stone, self.candidate_radius)
        if winning_move is not None:
            return winning_move

        blocking_move = find_immediate_win_by_simulation(board, opponent(self.stone), self.candidate_radius)
        if blocking_move is not None:
            return blocking_move

        self._ensure_hasher(board.size)
        self.stats = SearchStats()
        candidates = self._ordered_candidates(board, self.stone, limit=self.candidate_limit)
        best_move = candidates[0]
        best_value = -inf
        alpha = -inf
        beta = inf

        for row, col in candidates:
            next_board = board.with_move(row, col, self.stone)
            value = self._alpha_beta(
                next_board,
                depth=self.depth - 1,
                alpha=alpha,
                beta=beta,
                current_stone=opponent(self.stone),
                last_move=(row, col),
            )
            if value > best_value:
                best_value = value
                best_move = (row, col)
            alpha = max(alpha, best_value)

        return best_move

    def _ordered_candidates(
        self,
        board: Board,
        stone: int,
        *,
        limit: int | None,
    ) -> list[tuple[int, int]]:
        candidates = generate_candidate_moves(board, radius=self.candidate_radius)
        scored = [
            (_global_score_after_move(board, row, col, stone), row, col)
            for row, col in candidates
        ]
        scored.sort(reverse=True)
        if limit is not None and len(scored) > limit:
            scored = scored[:limit]
        return [(row, col) for _score, row, col in scored]

    def _candidate_limit_for_depth(self, depth: int) -> int:
        return self.candidate_limit


class AlphaBetaV3AI(AlphaBetaAI):
    """Stronger alpha-beta variant with richer shape scoring and tactical guards."""

    name = "v3"

    def _ordered_candidates(
        self,
        board: Board,
        stone: int,
        *,
        limit: int | None,
    ) -> list[tuple[int, int]]:
        candidates = generate_candidate_moves(board, radius=self.candidate_radius)
        scored = [
            (self._move_order_score(board, row, col, stone), row, col)
            for row, col in candidates
        ]
        scored.sort(reverse=True)

        selected: list[tuple[int, int]] = []
        seen: set[tuple[int, int]] = set()
        for _score, row, col in scored:
            move = (row, col)
            is_within_limit = limit is None or len(selected) < limit
            if is_within_limit or _is_v3_tactical_candidate(board, row, col, stone):
                if move not in seen:
                    selected.append(move)
                    seen.add(move)
        return selected

    def _move_order_score(self, board: Board, row: int, col: int, stone: int) -> int:
        center = (board.size - 1) / 2
        center_bonus = int((board.size - abs(center - row) - abs(center - col)) * 10)

        if _move_wins(board, row, col, stone):
            return WIN_SCORE
        if _move_wins(board, row, col, opponent(stone)):
            return WIN_SCORE - 1

        own_score = _v3_local_score_after_move(board, row, col, stone)
        blocking_score = _v3_local_score_after_move(board, row, col, opponent(stone))
        neighbor_bonus = _neighbor_count(board, row, col) * 20
        return own_score * 2 + int(blocking_score * 1.5) + center_bonus + neighbor_bonus

    def _evaluate(self, board: Board) -> int:
        key = self._hash(board)
        if key in self._eval_cache:
            self.stats.cache_hits += 1
            return self._eval_cache[key]

        own = _evaluate_for_v3(board, self.stone)
        enemy = _evaluate_for_v3(board, opponent(self.stone))
        score = own - int(enemy * 1.16) + _center_bias(board, self.stone)
        self._eval_cache[key] = score
        return score


def generate_candidate_moves(board: Board, radius: int = 2) -> list[tuple[int, int]]:
    if board.is_empty():
        center = board.size // 2
        return [(center, center)]

    moves: set[tuple[int, int]] = set()
    for row, col, _stone in board.stones():
        for row_delta in range(-radius, radius + 1):
            for col_delta in range(-radius, radius + 1):
                if row_delta == 0 and col_delta == 0:
                    continue
                next_row = row + row_delta
                next_col = col + col_delta
                if board.is_empty_at(next_row, next_col):
                    moves.add((next_row, next_col))
    return sorted(moves)


def find_immediate_win(
    board: Board,
    stone: int,
    radius: int = 2,
) -> tuple[int, int] | None:
    for row, col in generate_candidate_moves(board, radius=radius):
        if _move_wins(board, row, col, stone):
            return row, col
    return None


def find_immediate_win_by_simulation(
    board: Board,
    stone: int,
    radius: int = 2,
) -> tuple[int, int] | None:
    for row, col in generate_candidate_moves(board, radius=radius):
        child = board.with_move(row, col, stone)
        if child.winner_from(row, col) == stone:
            return row, col
    return None


def _move_wins(board: Board, row: int, col: int, stone: int) -> bool:
    if not board.is_empty_at(row, col):
        return False
    for row_step, col_step in DIRECTIONS:
        total = 1
        total += _count_stones(board, row, col, row_step, col_step, stone)
        total += _count_stones(board, row, col, -row_step, -col_step, stone)
        if total >= board.win_length:
            return True
    return False


def _count_stones(
    board: Board,
    row: int,
    col: int,
    row_step: int,
    col_step: int,
    stone: int,
) -> int:
    count = 0
    row += row_step
    col += col_step
    while board.is_on_board(row, col) and board.grid[row][col] == stone:
        count += 1
        row += row_step
        col += col_step
    return count


def _local_score_after_move(board: Board, row: int, col: int, stone: int) -> int:
    if not board.is_empty_at(row, col):
        return 0

    score = 0
    for row_step, col_step in DIRECTIONS:
        left_count, left_open = _count_line_side(board, row, col, -row_step, -col_step, stone)
        right_count, right_open = _count_line_side(board, row, col, row_step, col_step, stone)
        count = 1 + left_count + right_count
        open_ends = int(left_open) + int(right_open)
        score += _score_shape(count, open_ends)
    return score


def _global_score_after_move(board: Board, row: int, col: int, stone: int) -> int:
    if not board.is_empty_at(row, col):
        return -WIN_SCORE
    child = board.with_move(row, col, stone)
    own = _evaluate_for(child, stone)
    enemy = _evaluate_for(child, opponent(stone))
    return own - int(enemy * 1.12) + _center_bias(child, stone)


def _v3_local_score_after_move(board: Board, row: int, col: int, stone: int) -> int:
    if not board.is_empty_at(row, col):
        return 0

    score = 0
    for row_step, col_step in DIRECTIONS:
        line = _line_through_move(board, row, col, row_step, col_step, stone)
        score += _score_line_v3(line, stone)
    return score


def _line_through_move(
    board: Board,
    row: int,
    col: int,
    row_step: int,
    col_step: int,
    stone: int,
) -> list[int]:
    line = []
    radius = board.win_length + 1
    other = opponent(stone)
    for offset in range(-radius, radius + 1):
        current_row = row + offset * row_step
        current_col = col + offset * col_step
        if offset == 0:
            line.append(stone)
        elif board.is_on_board(current_row, current_col):
            line.append(board.grid[current_row][current_col])
        else:
            line.append(other)
    return line


def _is_v3_tactical_candidate(board: Board, row: int, col: int, stone: int) -> bool:
    other = opponent(stone)
    if _move_wins(board, row, col, stone) or _move_wins(board, row, col, other):
        return True

    own_score = _v3_local_score_after_move(board, row, col, stone)
    block_score = _v3_local_score_after_move(board, row, col, other)
    return own_score >= OPEN_FOUR or block_score >= OPEN_FOUR or own_score >= OPEN_THREE * 2


def _count_line_side(
    board: Board,
    row: int,
    col: int,
    row_step: int,
    col_step: int,
    stone: int,
) -> tuple[int, bool]:
    count = 0
    row += row_step
    col += col_step
    while board.is_on_board(row, col) and board.grid[row][col] == stone:
        count += 1
        row += row_step
        col += col_step
    is_open = board.is_on_board(row, col) and board.grid[row][col] == EMPTY
    return count, is_open


def _score_shape(count: int, open_ends: int) -> int:
    if count >= 5:
        return WIN_SCORE
    if count == 4:
        return OPEN_FOUR if open_ends == 2 else FOUR if open_ends == 1 else 0
    if count == 3:
        return OPEN_THREE if open_ends == 2 else THREE if open_ends == 1 else 0
    if count == 2:
        return OPEN_TWO if open_ends == 2 else TWO if open_ends == 1 else 0
    if count == 1:
        return SINGLE if open_ends == 2 else 0
    return 0


def _neighbor_count(board: Board, row: int, col: int, radius: int = 2) -> int:
    count = 0
    for row_delta in range(-radius, radius + 1):
        for col_delta in range(-radius, radius + 1):
            if row_delta == 0 and col_delta == 0:
                continue
            next_row = row + row_delta
            next_col = col + col_delta
            if board.is_on_board(next_row, next_col) and board.grid[next_row][next_col] != EMPTY:
                count += 1
    return count


def _evaluate_for(board: Board, stone: int) -> int:
    score = 0
    for line in _lines(board):
        score += _score_line(line, stone)
    return score


def _evaluate_for_v3(board: Board, stone: int) -> int:
    score = 0
    for line in _lines(board):
        score += _score_line_v3(line, stone)
    return score


def _score_line(line: list[int], stone: int) -> int:
    other = opponent(stone)
    score = 0
    window = 5
    for start in range(0, len(line) - window + 1):
        segment = line[start : start + window]
        own = segment.count(stone)
        enemy = segment.count(other)
        empty = segment.count(EMPTY)
        if enemy:
            continue
        if own == 5:
            score += WIN_SCORE
            continue

        left_open = start > 0 and line[start - 1] == EMPTY
        right_open = start + window < len(line) and line[start + window] == EMPTY
        open_ends = int(left_open) + int(right_open)

        if own == 4 and empty == 1:
            score += OPEN_FOUR if open_ends == 2 else FOUR
        elif own == 3 and empty == 2:
            score += OPEN_THREE if open_ends == 2 else THREE
        elif own == 2 and empty == 3:
            score += OPEN_TWO if open_ends == 2 else TWO
        elif own == 1 and empty == 4:
            score += SINGLE
    return score


OPEN_FOUR_PATTERNS = (".XXXX.", ".XXX.X.", ".XX.XX.", ".X.XXX.")
FOUR_PATTERNS = ("XXXX.", ".XXXX", "XXX.X", "XX.XX", "X.XXX")
OPEN_THREE_PATTERNS = ("..XXX.", ".XXX..", ".XX.X.", ".X.XX.")
THREE_PATTERNS = ("XXX..", "..XXX", "XX.X.", ".X.XX", "X.XX.", ".XX.X", "X.X.X")
OPEN_TWO_PATTERNS = ("..XX.", ".XX..", ".X.X.")


def _score_line_v3(line: list[int], stone: int) -> int:
    text = _line_to_pattern(line, stone)
    score = max(_score_line(line, stone), _count_pattern_occurrences(text, ("XXXXX",)) * WIN_SCORE)
    score += _count_pattern_occurrences(text, OPEN_FOUR_PATTERNS) * OPEN_FOUR
    score += _count_pattern_occurrences(text, FOUR_PATTERNS) * FOUR
    score += _count_pattern_occurrences(text, OPEN_THREE_PATTERNS) * OPEN_THREE
    score += _count_pattern_occurrences(text, THREE_PATTERNS) * THREE
    score += _count_pattern_occurrences(text, OPEN_TWO_PATTERNS) * OPEN_TWO
    return score


def _line_to_pattern(line: list[int], stone: int) -> str:
    other = opponent(stone)
    chars = []
    for value in line:
        if value == stone:
            chars.append("X")
        elif value == EMPTY:
            chars.append(".")
        elif value == other:
            chars.append("O")
        else:
            chars.append("O")
    return "".join(chars)


def _count_pattern_occurrences(text: str, patterns: tuple[str, ...]) -> int:
    total = 0
    for pattern in patterns:
        start = 0
        while True:
            index = text.find(pattern, start)
            if index == -1:
                break
            total += 1
            start = index + 1
    return total


def _lines(board: Board) -> list[list[int]]:
    size = board.size
    lines: list[list[int]] = []

    lines.extend([row[:] for row in board.grid])
    lines.extend([[board.grid[row][col] for row in range(size)] for col in range(size)])

    for start_col in range(size):
        diagonal = []
        row, col = 0, start_col
        while row < size and col < size:
            diagonal.append(board.grid[row][col])
            row += 1
            col += 1
        if len(diagonal) >= board.win_length:
            lines.append(diagonal)

    for start_row in range(1, size):
        diagonal = []
        row, col = start_row, 0
        while row < size and col < size:
            diagonal.append(board.grid[row][col])
            row += 1
            col += 1
        if len(diagonal) >= board.win_length:
            lines.append(diagonal)

    for start_col in range(size):
        diagonal = []
        row, col = 0, start_col
        while row < size and col >= 0:
            diagonal.append(board.grid[row][col])
            row += 1
            col -= 1
        if len(diagonal) >= board.win_length:
            lines.append(diagonal)

    for start_row in range(1, size):
        diagonal = []
        row, col = start_row, size - 1
        while row < size and col >= 0:
            diagonal.append(board.grid[row][col])
            row += 1
            col -= 1
        if len(diagonal) >= board.win_length:
            lines.append(diagonal)

    return lines


def _center_bias(board: Board, stone: int) -> int:
    center = (board.size - 1) / 2
    score = 0
    for row, col, value in board.stones():
        distance = abs(center - row) + abs(center - col)
        bias = int((board.size - distance) * 3)
        if value == stone:
            score += bias
        else:
            score -= bias
    return score
