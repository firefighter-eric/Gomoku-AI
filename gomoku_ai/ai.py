from __future__ import annotations

import random
from dataclasses import dataclass
from math import inf

from gomoku_ai.core import BLACK, DRAW, EMPTY, WHITE, Board, MoveUndo, opponent
from gomoku_ai.rust_backend import choose_move_v5 as _rust_choose_move_v5
from gomoku_ai.rust_backend import rust_backend_name, rust_backend_available

WIN_SCORE = 10_000_000
OPEN_FOUR = 1_000_000
DOUBLE_FOUR = 2_000_000
FOUR_THREE = 1_200_000
FOUR = 100_000
DOUBLE_THREE = 80_000
OPEN_THREE = 12_000
THREE = 1_500
OPEN_TWO = 350
TWO = 80
SINGLE = 8
DIRECTIONS = ((0, 1), (1, 0), (1, 1), (1, -1))
TT_EXACT = "exact"
TT_LOWER = "lower"
TT_UPPER = "upper"


@dataclass
class SearchStats:
    nodes: int = 0
    cache_hits: int = 0


@dataclass(frozen=True)
class V4TranspositionEntry:
    depth: int
    value: int
    flag: str
    best_move: tuple[int, int] | None = None


@dataclass(frozen=True)
class V3MoveThreats:
    open_fours: int = 0
    fours: int = 0
    open_threes: int = 0
    threes: int = 0

    @property
    def four_threats(self) -> int:
        return self.open_fours + self.fours

    @property
    def has_double_four(self) -> bool:
        return self.four_threats >= 2

    @property
    def has_four_three(self) -> bool:
        return self.four_threats >= 1 and self.open_threes >= 1

    @property
    def has_double_three(self) -> bool:
        return self.open_threes >= 2

    @property
    def is_forcing(self) -> bool:
        return self.has_double_four or self.has_four_three or self.has_double_three


@dataclass(frozen=True)
class V4LineAnalysis:
    score: int
    threats: V3MoveThreats


@dataclass(frozen=True)
class V4MoveAnalysis:
    score: int
    threats: V3MoveThreats


@dataclass(frozen=True)
class V4CandidateAnalysis:
    score: int
    own_threats: V3MoveThreats
    block_threats: V3MoveThreats
    tactical: bool


@dataclass(frozen=True)
class _V4FrontierUndo:
    move: tuple[int, int]
    previous_count: int | None
    added_moves: tuple[tuple[int, int], ...]


@dataclass(frozen=True)
class _V4EvaluationUndo:
    own_score: int
    enemy_score: int
    center_bias: int
    affected_own_score: int
    affected_enemy_score: int


@dataclass(frozen=True)
class _V4SearchUndo:
    board_undo: MoveUndo
    frontier_undo: _V4FrontierUndo
    evaluation_undo: _V4EvaluationUndo


class _V4CandidateFrontier:
    def __init__(self, board: Board, radius: int) -> None:
        self.radius = radius
        self._counts = self._build_counts(board, radius)

    @classmethod
    def _build_counts(cls, board: Board, radius: int) -> dict[tuple[int, int], int]:
        if board.is_empty():
            center = board.size // 2
            return {(center, center): 1}

        counts: dict[tuple[int, int], int] = {}
        for row, col, _stone in board.stones():
            for next_row, next_col in _neighbor_points(board, row, col, radius):
                if board.is_empty_at(next_row, next_col):
                    move = (next_row, next_col)
                    counts[move] = counts.get(move, 0) + 1
        return counts

    def candidates(self) -> list[tuple[int, int]]:
        return sorted(self._counts)

    def make_move(self, board: Board, row: int, col: int) -> _V4FrontierUndo:
        move = (row, col)
        previous_count = self._counts.pop(move, None)
        added_moves: list[tuple[int, int]] = []

        for next_row, next_col in _neighbor_points(board, row, col, self.radius):
            if board.is_empty_at(next_row, next_col):
                added = (next_row, next_col)
                self._counts[added] = self._counts.get(added, 0) + 1
                added_moves.append(added)

        return _V4FrontierUndo(
            move=move,
            previous_count=previous_count,
            added_moves=tuple(added_moves),
        )

    def undo_move(self, undo: _V4FrontierUndo) -> None:
        for move in reversed(undo.added_moves):
            count = self._counts[move] - 1
            if count <= 0:
                del self._counts[move]
            else:
                self._counts[move] = count

        if undo.previous_count is not None:
            self._counts[undo.move] = undo.previous_count


class _V4IncrementalEvaluator:
    def __init__(self, board: Board, stone: int) -> None:
        self.stone = stone
        self.enemy = opponent(stone)
        self.own_score = _evaluate_for_v4(board, stone)
        self.enemy_score = _evaluate_for_v4(board, self.enemy)
        self.center_bias = _center_bias(board, stone)

    def score(self) -> int:
        return self.own_score - int(self.enemy_score * 1.16) + self.center_bias

    def prepare_move(self, board: Board, row: int, col: int) -> _V4EvaluationUndo:
        own, enemy = self._affected_scores(board, row, col)
        return _V4EvaluationUndo(
            own_score=self.own_score,
            enemy_score=self.enemy_score,
            center_bias=self.center_bias,
            affected_own_score=own,
            affected_enemy_score=enemy,
        )

    def finish_move(
        self,
        board: Board,
        row: int,
        col: int,
        stone: int,
        undo: _V4EvaluationUndo,
    ) -> None:
        own, enemy = self._affected_scores(board, row, col)
        self.own_score += own - undo.affected_own_score
        self.enemy_score += enemy - undo.affected_enemy_score
        self.center_bias += _center_bias_for_stone(board, row, col, stone, self.stone)

    def undo_move(self, undo: _V4EvaluationUndo) -> None:
        self.own_score = undo.own_score
        self.enemy_score = undo.enemy_score
        self.center_bias = undo.center_bias

    def _affected_scores(self, board: Board, row: int, col: int) -> tuple[int, int]:
        own = 0
        enemy = 0
        for line in _lines_through_point(board, row, col):
            own += _score_line_v4(line, self.stone)
            enemy += _score_line_v4(line, self.enemy)
        return own, enemy


class _V4SearchState:
    def __init__(self, board: Board, stone: int, candidate_radius: int) -> None:
        self.frontier = _V4CandidateFrontier(board, candidate_radius)
        self.evaluator = _V4IncrementalEvaluator(board, stone)

    def make_move(self, board: Board, row: int, col: int, stone: int) -> _V4SearchUndo:
        evaluation_undo = self.evaluator.prepare_move(board, row, col)
        board_undo = board.make_move(row, col, stone)
        frontier_undo = self.frontier.make_move(board, row, col)
        self.evaluator.finish_move(board, row, col, stone, evaluation_undo)
        return _V4SearchUndo(
            board_undo=board_undo,
            frontier_undo=frontier_undo,
            evaluation_undo=evaluation_undo,
        )

    def undo_move(self, board: Board, undo: _V4SearchUndo) -> None:
        board.undo_move(undo.board_undo)
        self.frontier.undo_move(undo.frontier_undo)
        self.evaluator.undo_move(undo.evaluation_undo)


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

    def update_hash(self, value: int, row: int, col: int, stone: int) -> int:
        if stone == BLACK:
            return value ^ self.black[row][col]
        if stone == WHITE:
            return value ^ self.white[row][col]
        raise ValueError(f"invalid stone: {stone!r}")


class AlphaBetaAI:
    """Alpha-beta Gomoku AI with heuristic move ordering and Zobrist caches."""

    name = "v2"

    def __init__(
        self,
        stone: int,
        depth: int = 5,
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
        self._transposition_table: dict[tuple[int, int], V4TranspositionEntry] = {}
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
            self._transposition_table.clear()

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


class AlphaBetaV4AI(AlphaBetaV3AI):
    """V4 alpha-beta variant with V3 tactics plus reused candidate analysis."""

    name = "v4"

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
        board_hash = self._hash(board)
        state = _V4SearchState(board, self.stone, self.candidate_radius)
        candidates = self._ordered_candidates_from(
            board,
            self.stone,
            state.frontier.candidates(),
            limit=self.candidate_limit,
            preferred_move=None,
        )
        best_move = candidates[0]
        best_value = -inf
        alpha = -inf
        beta = inf

        for row, col in candidates:
            undo = state.make_move(board, row, col, self.stone)
            child_hash = self._hash_after_move(board_hash, row, col, self.stone)
            try:
                value = self._alpha_beta_v4(
                    board,
                    depth=self.depth - 1,
                    alpha=alpha,
                    beta=beta,
                    current_stone=opponent(self.stone),
                    last_move=(row, col),
                    board_hash=child_hash,
                    state=state,
                )
            finally:
                state.undo_move(board, undo)
            if value > best_value:
                best_value = value
                best_move = (row, col)
            alpha = max(alpha, best_value)

        return best_move

    def _alpha_beta_v4(
        self,
        board: Board,
        depth: int,
        alpha: float,
        beta: float,
        current_stone: int,
        last_move: tuple[int, int] | None,
        board_hash: int,
        state: _V4SearchState,
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
            return state.evaluator.score()

        key = (board_hash, current_stone)
        original_alpha = alpha
        original_beta = beta
        cached = self._transposition_table.get(key)
        if cached is not None and cached.depth >= depth:
            if cached.flag == TT_EXACT:
                self.stats.cache_hits += 1
                return cached.value
            if cached.flag == TT_LOWER:
                alpha = max(alpha, cached.value)
            elif cached.flag == TT_UPPER:
                beta = min(beta, cached.value)
            if alpha >= beta:
                self.stats.cache_hits += 1
                return cached.value

        maximizing = current_stone == self.stone
        candidates = self._ordered_candidates_from(
            board,
            current_stone,
            state.frontier.candidates(),
            limit=self._candidate_limit_for_depth(depth),
            preferred_move=cached.best_move if cached is not None else None,
        )
        if not candidates:
            return state.evaluator.score()

        best_move: tuple[int, int] | None = None

        if maximizing:
            value = -inf
            for row, col in candidates:
                undo = state.make_move(board, row, col, current_stone)
                child_hash = self._hash_after_move(board_hash, row, col, current_stone)
                try:
                    child_value = self._alpha_beta_v4(
                        board,
                        depth - 1,
                        alpha,
                        beta,
                        opponent(current_stone),
                        (row, col),
                        child_hash,
                        state,
                    )
                finally:
                    state.undo_move(board, undo)
                if child_value > value:
                    value = child_value
                    best_move = (row, col)
                alpha = max(alpha, value)
                if beta <= alpha:
                    break
        else:
            value = inf
            for row, col in candidates:
                undo = state.make_move(board, row, col, current_stone)
                child_hash = self._hash_after_move(board_hash, row, col, current_stone)
                try:
                    child_value = self._alpha_beta_v4(
                        board,
                        depth - 1,
                        alpha,
                        beta,
                        opponent(current_stone),
                        (row, col),
                        child_hash,
                        state,
                    )
                finally:
                    state.undo_move(board, undo)
                if child_value < value:
                    value = child_value
                    best_move = (row, col)
                beta = min(beta, value)
                if beta <= alpha:
                    break

        result = int(value)
        if result <= original_alpha:
            flag = TT_UPPER
        elif result >= original_beta:
            flag = TT_LOWER
        else:
            flag = TT_EXACT
        self._store_transposition(
            key,
            V4TranspositionEntry(
                depth=depth,
                value=result,
                flag=flag,
                best_move=best_move,
            ),
        )
        return result

    def _ordered_candidates(
        self,
        board: Board,
        stone: int,
        *,
        limit: int | None,
    ) -> list[tuple[int, int]]:
        candidates = generate_candidate_moves(board, radius=self.candidate_radius)
        return self._ordered_candidates_from(
            board,
            stone,
            candidates,
            limit=limit,
            preferred_move=None,
        )

    def _ordered_candidates_from(
        self,
        board: Board,
        stone: int,
        candidates: list[tuple[int, int]],
        *,
        limit: int | None,
        preferred_move: tuple[int, int] | None,
    ) -> list[tuple[int, int]]:
        scored = []
        for row, col in candidates:
            if not board.is_empty_at(row, col):
                continue
            analysis = _v4_candidate_analysis(board, row, col, stone)
            score = analysis.score
            if preferred_move == (row, col):
                score += WIN_SCORE * 2
            scored.append((score, row, col, analysis))
        scored.sort(reverse=True)

        selected: list[tuple[int, int]] = []
        seen: set[tuple[int, int]] = set()
        for _score, row, col, analysis in scored:
            move = (row, col)
            is_within_limit = limit is None or len(selected) < limit
            if is_within_limit or analysis.tactical:
                if move not in seen:
                    selected.append(move)
                    seen.add(move)
        return selected

    def _move_order_score(self, board: Board, row: int, col: int, stone: int) -> int:
        return _v4_candidate_analysis(board, row, col, stone).score

    def _evaluate(self, board: Board) -> int:
        return self._evaluate_with_hash(board, self._hash(board))

    def _evaluate_with_hash(self, board: Board, board_hash: int) -> int:
        key = board_hash
        if key in self._eval_cache:
            self.stats.cache_hits += 1
            return self._eval_cache[key]

        score = _v4_static_score(board, self.stone)
        self._eval_cache[key] = score
        return score

    def _hash_after_move(self, board_hash: int, row: int, col: int, stone: int) -> int:
        assert self._hasher is not None
        return self._hasher.update_hash(board_hash, row, col, stone)

    def _store_transposition(
        self,
        key: tuple[int, int],
        entry: V4TranspositionEntry,
    ) -> None:
        current = self._transposition_table.get(key)
        if current is None or entry.depth >= current.depth:
            self._transposition_table[key] = entry


class AlphaBetaV5AI(AlphaBetaV4AI):
    """V5 alpha-beta variant that delegates the search core to the Rust engine."""

    name = "v5"

    def __init__(
        self,
        stone: int,
        depth: int = 5,
        candidate_radius: int = 2,
        candidate_limit: int = 18,
        seed: int = 20260521,
    ) -> None:
        super().__init__(
            stone,
            depth=depth,
            candidate_radius=candidate_radius,
            candidate_limit=candidate_limit,
            seed=seed,
        )
        self.backend = rust_backend_name()

    def choose_move(self, board: Board) -> tuple[int, int]:
        if rust_backend_available():
            row, col, nodes, cache_hits = _rust_choose_move_v5(
                board,
                self.stone,
                depth=self.depth,
                candidate_radius=self.candidate_radius,
                candidate_limit=self.candidate_limit,
                seed=self.seed,
            )
            if not board.is_empty_at(row, col):
                raise ValueError(f"Rust engine returned an occupied move: ({row}, {col})")
            self.stats = SearchStats(nodes=nodes, cache_hits=cache_hits)
            self.backend = "rust-engine"
            return row, col

        self.backend = "python-v4-fallback"
        return super().choose_move(board)


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


def _neighbor_points(
    board: Board,
    row: int,
    col: int,
    radius: int,
) -> list[tuple[int, int]]:
    points = []
    for row_delta in range(-radius, radius + 1):
        for col_delta in range(-radius, radius + 1):
            if row_delta == 0 and col_delta == 0:
                continue
            next_row = row + row_delta
            next_col = col + col_delta
            if board.is_on_board(next_row, next_col):
                points.append((next_row, next_col))
    return points


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
    open_fours = 0
    fours = 0
    open_threes = 0
    threes = 0
    for row_step, col_step in DIRECTIONS:
        line = _line_through_move(board, row, col, row_step, col_step, stone)
        score += _score_line_v3(line, stone)
        line_threats = _v3_line_threats(line, stone)
        open_fours += line_threats.open_fours
        fours += line_threats.fours
        open_threes += line_threats.open_threes
        threes += line_threats.threes
    return score + _v3_threat_bonus(
        V3MoveThreats(
            open_fours=open_fours,
            fours=fours,
            open_threes=open_threes,
            threes=threes,
        )
    )


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

    own_threats = _v3_threats_after_move(board, row, col, stone)
    block_threats = _v3_threats_after_move(board, row, col, other)
    return (
        own_threats.four_threats >= 1
        or block_threats.four_threats >= 1
        or own_threats.is_forcing
        or block_threats.is_forcing
    )


def _v4_candidate_analysis(board: Board, row: int, col: int, stone: int) -> V4CandidateAnalysis:
    if _move_wins(board, row, col, stone):
        return V4CandidateAnalysis(
            score=WIN_SCORE,
            own_threats=V3MoveThreats(),
            block_threats=V3MoveThreats(),
            tactical=True,
        )

    other = opponent(stone)
    if _move_wins(board, row, col, other):
        return V4CandidateAnalysis(
            score=WIN_SCORE - 1,
            own_threats=V3MoveThreats(),
            block_threats=V3MoveThreats(),
            tactical=True,
        )

    center = (board.size - 1) / 2
    center_bonus = int((board.size - abs(center - row) - abs(center - col)) * 10)
    own = _v4_move_analysis_after_move(board, row, col, stone)
    block = _v4_move_analysis_after_move(board, row, col, other)
    neighbor_bonus = _neighbor_count(board, row, col) * 20
    tactical = (
        own.threats.four_threats >= 1
        or block.threats.four_threats >= 1
        or own.threats.is_forcing
        or block.threats.is_forcing
    )
    return V4CandidateAnalysis(
        score=own.score * 2 + int(block.score * 1.5) + center_bonus + neighbor_bonus,
        own_threats=own.threats,
        block_threats=block.threats,
        tactical=tactical,
    )


def _v4_move_analysis_after_move(board: Board, row: int, col: int, stone: int) -> V4MoveAnalysis:
    if not board.is_empty_at(row, col):
        return V4MoveAnalysis(score=0, threats=V3MoveThreats())

    score = 0
    open_fours = 0
    fours = 0
    open_threes = 0
    threes = 0
    for row_step, col_step in DIRECTIONS:
        line = _line_through_move(board, row, col, row_step, col_step, stone)
        line_analysis = _analyze_line_v4(line, stone)
        score += line_analysis.score
        open_fours += line_analysis.threats.open_fours
        fours += line_analysis.threats.fours
        open_threes += line_analysis.threats.open_threes
        threes += line_analysis.threats.threes

    threats = V3MoveThreats(
        open_fours=open_fours,
        fours=fours,
        open_threes=open_threes,
        threes=threes,
    )
    return V4MoveAnalysis(score=score + _v3_threat_bonus(threats), threats=threats)


def _v3_threats_after_move(board: Board, row: int, col: int, stone: int) -> V3MoveThreats:
    if not board.is_empty_at(row, col):
        return V3MoveThreats()

    open_fours = 0
    fours = 0
    open_threes = 0
    threes = 0
    for row_step, col_step in DIRECTIONS:
        line = _line_through_move(board, row, col, row_step, col_step, stone)
        line_threats = _v3_line_threats(line, stone)
        open_fours += line_threats.open_fours
        fours += line_threats.fours
        open_threes += line_threats.open_threes
        threes += line_threats.threes
    return V3MoveThreats(
        open_fours=open_fours,
        fours=fours,
        open_threes=open_threes,
        threes=threes,
    )


def _v4_threats_after_move(board: Board, row: int, col: int, stone: int) -> V3MoveThreats:
    return _v4_move_analysis_after_move(board, row, col, stone).threats


def _v3_line_threats(line: list[int], stone: int) -> V3MoveThreats:
    text = _line_to_pattern(line, stone)
    has_open_four = _contains_any_pattern(text, OPEN_FOUR_PATTERNS)
    has_four = _contains_any_pattern(text, FOUR_PATTERNS) and not has_open_four
    has_open_three = _contains_any_pattern(text, OPEN_THREE_PATTERNS) and not has_open_four and not has_four
    has_three = _contains_any_pattern(text, THREE_PATTERNS) and not has_open_four and not has_four and not has_open_three
    return V3MoveThreats(
        open_fours=int(has_open_four),
        fours=int(has_four),
        open_threes=int(has_open_three),
        threes=int(has_three),
    )


def _v4_line_threats(line: list[int], stone: int) -> V3MoveThreats:
    return _analyze_line_v4(line, stone).threats


def _v3_threat_bonus(threats: V3MoveThreats) -> int:
    score = 0
    if threats.has_double_four:
        score += DOUBLE_FOUR
    if threats.has_four_three:
        score += FOUR_THREE
    if threats.has_double_three:
        score += DOUBLE_THREE
    return score


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


def _evaluate_for_v4(board: Board, stone: int) -> int:
    score = 0
    for line in _lines(board):
        score += _score_line_v4(line, stone)
    return score


def _v4_static_score(board: Board, stone: int) -> int:
    own = _evaluate_for_v4(board, stone)
    enemy = _evaluate_for_v4(board, opponent(stone))
    return own - int(enemy * 1.16) + _center_bias(board, stone)


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


def _score_line_v4(line: list[int], stone: int) -> int:
    return _analyze_line_v4(line, stone).score


def _analyze_line_v4(line: list[int], stone: int) -> V4LineAnalysis:
    text = _line_to_pattern(line, stone)
    win_count = _count_pattern_occurrences(text, ("XXXXX",))
    open_four_count = _count_pattern_occurrences(text, OPEN_FOUR_PATTERNS)
    four_count = _count_pattern_occurrences(text, FOUR_PATTERNS)
    open_three_count = _count_pattern_occurrences(text, OPEN_THREE_PATTERNS)
    three_count = _count_pattern_occurrences(text, THREE_PATTERNS)
    open_two_count = _count_pattern_occurrences(text, OPEN_TWO_PATTERNS)

    score = max(_score_text_windows(text), win_count * WIN_SCORE)
    score += open_four_count * OPEN_FOUR
    score += four_count * FOUR
    score += open_three_count * OPEN_THREE
    score += three_count * THREE
    score += open_two_count * OPEN_TWO

    has_open_four = open_four_count > 0
    has_four = four_count > 0 and not has_open_four
    has_open_three = open_three_count > 0 and not has_open_four and not has_four
    has_three = three_count > 0 and not has_open_four and not has_four and not has_open_three
    threats = V3MoveThreats(
        open_fours=int(has_open_four),
        fours=int(has_four),
        open_threes=int(has_open_three),
        threes=int(has_three),
    )
    return V4LineAnalysis(score=score, threats=threats)


def _score_text_windows(text: str) -> int:
    score = 0
    window = 5
    for start in range(0, len(text) - window + 1):
        segment = text[start : start + window]
        if "O" in segment:
            continue

        own = segment.count("X")
        empty = segment.count(".")
        if own == 5:
            score += WIN_SCORE
            continue

        left_open = start > 0 and text[start - 1] == "."
        right_open = start + window < len(text) and text[start + window] == "."
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


def _contains_any_pattern(text: str, patterns: tuple[str, ...]) -> bool:
    return any(pattern in text for pattern in patterns)


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


def _lines_through_point(board: Board, row: int, col: int) -> list[list[int]]:
    size = board.size
    lines = [
        board.grid[row][:],
        [board.grid[current_row][col] for current_row in range(size)],
    ]

    diagonal = []
    current_row = row - min(row, col)
    current_col = col - min(row, col)
    while current_row < size and current_col < size:
        diagonal.append(board.grid[current_row][current_col])
        current_row += 1
        current_col += 1
    if len(diagonal) >= board.win_length:
        lines.append(diagonal)

    diagonal = []
    distance_to_edge = min(row, size - 1 - col)
    current_row = row - distance_to_edge
    current_col = col + distance_to_edge
    while current_row < size and current_col >= 0:
        diagonal.append(board.grid[current_row][current_col])
        current_row += 1
        current_col -= 1
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


def _center_bias_for_stone(board: Board, row: int, col: int, stone: int, perspective: int) -> int:
    center = (board.size - 1) / 2
    distance = abs(center - row) + abs(center - col)
    bias = int((board.size - distance) * 3)
    return bias if stone == perspective else -bias
