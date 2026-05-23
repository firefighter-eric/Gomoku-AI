use std::collections::HashMap;

const EMPTY: i8 = 0;
const BLACK: i8 = 1;
const WHITE: i8 = -1;
const DRAW: i8 = 2;

const WIN_SCORE: i64 = 10_000_000;
const OPEN_FOUR: i64 = 1_000_000;
const DOUBLE_FOUR: i64 = 2_000_000;
const FOUR_THREE: i64 = 1_200_000;
const FOUR: i64 = 100_000;
const DOUBLE_THREE: i64 = 80_000;
const OPEN_THREE: i64 = 12_000;
const THREE: i64 = 1_500;
const OPEN_TWO: i64 = 350;
const TWO: i64 = 80;
const SINGLE: i64 = 8;
const INF: i64 = 9_000_000_000_000;
const DIRECTIONS: [(isize, isize); 4] = [(0, 1), (1, 0), (1, 1), (1, -1)];

const OPEN_FOUR_PATTERNS: [&[u8]; 4] = [b".XXXX.", b".XXX.X.", b".XX.XX.", b".X.XXX."];
const FOUR_PATTERNS: [&[u8]; 5] = [b"XXXX.", b".XXXX", b"XXX.X", b"XX.XX", b"X.XXX"];
const OPEN_THREE_PATTERNS: [&[u8]; 4] = [b"..XXX.", b".XXX..", b".XX.X.", b".X.XX."];
const THREE_PATTERNS: [&[u8]; 7] = [
    b"XXX..", b"..XXX", b"XX.X.", b".X.XX", b"X.XX.", b".XX.X", b"X.X.X",
];
const OPEN_TWO_PATTERNS: [&[u8]; 3] = [b"..XX.", b".XX..", b".X.X."];

#[derive(Clone)]
struct Board {
    size: usize,
    win_length: usize,
    grid: Vec<i8>,
    move_count: usize,
}

impl Board {
    fn from_flat(grid: Vec<i8>, size: usize, win_length: usize) -> Result<Self, String> {
        if size < 1 {
            return Err("board size must be positive".to_string());
        }
        if win_length < 1 {
            return Err("win_length must be positive".to_string());
        }
        if size < win_length {
            return Err("board size must be at least win_length".to_string());
        }
        if grid.len() != size * size {
            return Err("grid length must match board size".to_string());
        }

        let mut move_count = 0;
        for &value in &grid {
            if value != EMPTY && value != BLACK && value != WHITE {
                return Err(format!("invalid stone: {value}"));
            }
            if value != EMPTY {
                move_count += 1;
            }
        }

        Ok(Self {
            size,
            win_length,
            grid,
            move_count,
        })
    }

    fn idx(&self, row: usize, col: usize) -> usize {
        row * self.size + col
    }

    fn row_col(&self, idx: usize) -> (usize, usize) {
        (idx / self.size, idx % self.size)
    }

    fn is_on_board(&self, row: isize, col: isize) -> bool {
        row >= 0 && col >= 0 && (row as usize) < self.size && (col as usize) < self.size
    }

    fn is_full(&self) -> bool {
        self.move_count == self.size * self.size
    }

    fn play_idx(&mut self, idx: usize, stone: i8) {
        debug_assert_eq!(self.grid[idx], EMPTY);
        self.grid[idx] = stone;
        self.move_count += 1;
    }

    fn undo_idx(&mut self, idx: usize) {
        debug_assert_ne!(self.grid[idx], EMPTY);
        self.grid[idx] = EMPTY;
        self.move_count -= 1;
    }

    fn legal_indices(&self) -> Vec<usize> {
        self.grid
            .iter()
            .enumerate()
            .filter_map(|(idx, &stone)| if stone == EMPTY { Some(idx) } else { None })
            .collect()
    }

    fn winner_from_idx(&self, idx: usize) -> Option<i8> {
        let (row, col) = self.row_col(idx);
        let stone = self.grid[idx];
        if stone == EMPTY {
            return if self.is_full() { Some(DRAW) } else { None };
        }

        for (row_step, col_step) in DIRECTIONS {
            let total = 1
                + self.count_direction(row, col, row_step, col_step, stone)
                + self.count_direction(row, col, -row_step, -col_step, stone);
            if total >= self.win_length {
                return Some(stone);
            }
        }

        if self.is_full() {
            Some(DRAW)
        } else {
            None
        }
    }

    fn count_direction(
        &self,
        row: usize,
        col: usize,
        row_step: isize,
        col_step: isize,
        stone: i8,
    ) -> usize {
        let mut count = 0;
        let mut current_row = row as isize + row_step;
        let mut current_col = col as isize + col_step;
        while self.is_on_board(current_row, current_col) {
            let idx = self.idx(current_row as usize, current_col as usize);
            if self.grid[idx] != stone {
                break;
            }
            count += 1;
            current_row += row_step;
            current_col += col_step;
        }
        count
    }
}

#[derive(Clone, Copy, Default)]
struct Threats {
    open_fours: i64,
    fours: i64,
    open_threes: i64,
    threes: i64,
}

impl Threats {
    fn four_threats(self) -> i64 {
        self.open_fours + self.fours
    }

    fn has_double_four(self) -> bool {
        self.four_threats() >= 2
    }

    fn has_four_three(self) -> bool {
        self.four_threats() >= 1 && self.open_threes >= 1
    }

    fn has_double_three(self) -> bool {
        self.open_threes >= 2
    }

    fn is_forcing(self) -> bool {
        self.has_double_four() || self.has_four_three() || self.has_double_three()
    }
}

#[derive(Clone, Copy)]
struct LineAnalysis {
    score: i64,
    threats: Threats,
}

#[derive(Clone, Copy)]
struct MoveAnalysis {
    score: i64,
    threats: Threats,
}

#[derive(Clone, Copy, PartialEq, Eq)]
enum BoundFlag {
    Exact,
    Lower,
    Upper,
}

#[derive(Clone, Copy)]
struct TranspositionEntry {
    depth: usize,
    value: i64,
    flag: BoundFlag,
    best_move: Option<usize>,
}

struct ZobristHasher {
    values: Vec<[u64; 2]>,
}

impl ZobristHasher {
    fn new(size: usize, seed: u64) -> Self {
        let mut state = seed ^ ((size as u64) << 32) ^ 0x9e37_79b9_7f4a_7c15_u64 ^ 0x2026_0523_u64;
        let mut values = Vec::with_capacity(size * size);
        for _ in 0..size * size {
            values.push([splitmix64(&mut state), splitmix64(&mut state)]);
        }
        Self { values }
    }

    fn hash_board(&self, board: &Board) -> u64 {
        let mut value = 0;
        for (idx, &stone) in board.grid.iter().enumerate() {
            if stone == BLACK {
                value ^= self.values[idx][0];
            } else if stone == WHITE {
                value ^= self.values[idx][1];
            }
        }
        value
    }

    fn update_hash(&self, board_hash: u64, idx: usize, stone: i8) -> u64 {
        if stone == BLACK {
            board_hash ^ self.values[idx][0]
        } else {
            board_hash ^ self.values[idx][1]
        }
    }
}

struct AlphaBetaRust {
    board: Board,
    stone: i8,
    depth: usize,
    candidate_radius: usize,
    candidate_limit: usize,
    hasher: ZobristHasher,
    transposition_table: HashMap<(u64, i8), TranspositionEntry>,
    nodes: u64,
    cache_hits: u64,
}

impl AlphaBetaRust {
    fn new(
        board: Board,
        stone: i8,
        depth: usize,
        candidate_radius: usize,
        candidate_limit: usize,
        seed: u64,
    ) -> Self {
        let hasher = ZobristHasher::new(board.size, seed);
        Self {
            board,
            stone,
            depth,
            candidate_radius,
            candidate_limit,
            hasher,
            transposition_table: HashMap::new(),
            nodes: 0,
            cache_hits: 0,
        }
    }

    fn choose_move(&mut self) -> Result<usize, String> {
        if self.board.move_count == 0 {
            let center = self.board.size / 2;
            return Ok(self.board.idx(center, center));
        }

        if let Some(idx) = find_immediate_win(&self.board, self.stone, self.candidate_radius) {
            return Ok(idx);
        }

        if let Some(idx) =
            find_immediate_win(&self.board, opponent(self.stone), self.candidate_radius)
        {
            return Ok(idx);
        }

        let board_hash = self.hasher.hash_board(&self.board);
        let mut candidates = ordered_candidates_from(
            &self.board,
            self.stone,
            generate_candidate_indices(&self.board, self.candidate_radius),
            Some(self.candidate_limit),
            None,
        );
        if candidates.is_empty() {
            candidates = self.board.legal_indices();
        }
        if candidates.is_empty() {
            return Err("cannot choose a move on a full board".to_string());
        }

        let mut best_move = candidates[0];
        let mut best_value = -INF;
        let mut alpha = -INF;
        let beta = INF;

        for idx in candidates {
            self.board.play_idx(idx, self.stone);
            let child_hash = self.hasher.update_hash(board_hash, idx, self.stone);
            let value = self.alpha_beta(
                self.depth - 1,
                alpha,
                beta,
                opponent(self.stone),
                Some(idx),
                child_hash,
            );
            self.board.undo_idx(idx);

            if value > best_value {
                best_value = value;
                best_move = idx;
            }
            alpha = alpha.max(best_value);
        }

        Ok(best_move)
    }

    fn alpha_beta(
        &mut self,
        depth: usize,
        mut alpha: i64,
        mut beta: i64,
        current_stone: i8,
        last_move: Option<usize>,
        board_hash: u64,
    ) -> i64 {
        self.nodes += 1;

        if let Some(idx) = last_move {
            if let Some(terminal) = self.board.winner_from_idx(idx) {
                if terminal == self.stone {
                    return WIN_SCORE + depth as i64;
                }
                if terminal == opponent(self.stone) {
                    return -WIN_SCORE - depth as i64;
                }
                if terminal == DRAW {
                    return 0;
                }
            }
        }

        if depth == 0 {
            return static_score(&self.board, self.stone);
        }

        let key = (board_hash, current_stone);
        let original_alpha = alpha;
        let original_beta = beta;
        let cached = self.transposition_table.get(&key).copied();
        if let Some(entry) = cached {
            if entry.depth >= depth {
                if entry.flag == BoundFlag::Exact {
                    self.cache_hits += 1;
                    return entry.value;
                }
                if entry.flag == BoundFlag::Lower {
                    alpha = alpha.max(entry.value);
                } else if entry.flag == BoundFlag::Upper {
                    beta = beta.min(entry.value);
                }
                if alpha >= beta {
                    self.cache_hits += 1;
                    return entry.value;
                }
            }
        }

        let candidates = ordered_candidates_from(
            &self.board,
            current_stone,
            generate_candidate_indices(&self.board, self.candidate_radius),
            Some(self.candidate_limit_for_depth(depth)),
            cached.and_then(|entry| entry.best_move),
        );
        if candidates.is_empty() {
            return static_score(&self.board, self.stone);
        }

        let maximizing = current_stone == self.stone;
        let mut best_move = None;

        let value = if maximizing {
            let mut value = -INF;
            for idx in candidates {
                self.board.play_idx(idx, current_stone);
                let child_hash = self.hasher.update_hash(board_hash, idx, current_stone);
                let child_value = self.alpha_beta(
                    depth - 1,
                    alpha,
                    beta,
                    opponent(current_stone),
                    Some(idx),
                    child_hash,
                );
                self.board.undo_idx(idx);

                if child_value > value {
                    value = child_value;
                    best_move = Some(idx);
                }
                alpha = alpha.max(value);
                if beta <= alpha {
                    break;
                }
            }
            value
        } else {
            let mut value = INF;
            for idx in candidates {
                self.board.play_idx(idx, current_stone);
                let child_hash = self.hasher.update_hash(board_hash, idx, current_stone);
                let child_value = self.alpha_beta(
                    depth - 1,
                    alpha,
                    beta,
                    opponent(current_stone),
                    Some(idx),
                    child_hash,
                );
                self.board.undo_idx(idx);

                if child_value < value {
                    value = child_value;
                    best_move = Some(idx);
                }
                beta = beta.min(value);
                if beta <= alpha {
                    break;
                }
            }
            value
        };

        let flag = if value <= original_alpha {
            BoundFlag::Upper
        } else if value >= original_beta {
            BoundFlag::Lower
        } else {
            BoundFlag::Exact
        };
        self.store_transposition(
            key,
            TranspositionEntry {
                depth,
                value,
                flag,
                best_move,
            },
        );
        value
    }

    fn candidate_limit_for_depth(&self, depth: usize) -> usize {
        if self.depth <= 2 {
            return self.candidate_limit;
        }
        if depth <= 1 {
            self.candidate_limit.min(10)
        } else if depth <= 2 {
            self.candidate_limit.min(14)
        } else {
            self.candidate_limit
        }
    }

    fn store_transposition(&mut self, key: (u64, i8), entry: TranspositionEntry) {
        let should_store = self
            .transposition_table
            .get(&key)
            .map(|current| entry.depth >= current.depth)
            .unwrap_or(true);
        if should_store {
            self.transposition_table.insert(key, entry);
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct MoveResult {
    pub row: usize,
    pub col: usize,
    pub nodes: u64,
    pub cache_hits: u64,
}

pub fn choose_move_v5_flat(
    grid: Vec<i8>,
    size: usize,
    win_length: usize,
    stone: i8,
    depth: usize,
    candidate_radius: usize,
    candidate_limit: usize,
    seed: u64,
) -> Result<MoveResult, String> {
    if stone != BLACK && stone != WHITE {
        return Err("AI stone must be BLACK or WHITE".to_string());
    }
    if depth < 1 {
        return Err("depth must be at least 1".to_string());
    }
    if candidate_limit < 1 {
        return Err("candidate_limit must be at least 1".to_string());
    }

    let board = Board::from_flat(grid, size, win_length)?;
    let mut ai = AlphaBetaRust::new(board, stone, depth, candidate_radius, candidate_limit, seed);
    let idx = ai.choose_move()?;
    let (row, col) = ai.board.row_col(idx);
    Ok(MoveResult {
        row,
        col,
        nodes: ai.nodes,
        cache_hits: ai.cache_hits,
    })
}

fn splitmix64(state: &mut u64) -> u64 {
    *state = state.wrapping_add(0x9e37_79b9_7f4a_7c15);
    let mut value = *state;
    value = (value ^ (value >> 30)).wrapping_mul(0xbf58_476d_1ce4_e5b9);
    value = (value ^ (value >> 27)).wrapping_mul(0x94d0_49bb_1331_11eb);
    value ^ (value >> 31)
}

fn opponent(stone: i8) -> i8 {
    if stone == BLACK {
        WHITE
    } else {
        BLACK
    }
}

fn generate_candidate_indices(board: &Board, radius: usize) -> Vec<usize> {
    if board.move_count == 0 {
        let center = board.size / 2;
        return vec![board.idx(center, center)];
    }

    let mut seen = vec![false; board.size * board.size];
    for (idx, &stone) in board.grid.iter().enumerate() {
        if stone == EMPTY {
            continue;
        }
        let (row, col) = board.row_col(idx);
        for row_delta in -(radius as isize)..=(radius as isize) {
            for col_delta in -(radius as isize)..=(radius as isize) {
                if row_delta == 0 && col_delta == 0 {
                    continue;
                }
                let next_row = row as isize + row_delta;
                let next_col = col as isize + col_delta;
                if board.is_on_board(next_row, next_col) {
                    let next_idx = board.idx(next_row as usize, next_col as usize);
                    if board.grid[next_idx] == EMPTY {
                        seen[next_idx] = true;
                    }
                }
            }
        }
    }

    seen.iter()
        .enumerate()
        .filter_map(|(idx, &value)| if value { Some(idx) } else { None })
        .collect()
}

fn find_immediate_win(board: &Board, stone: i8, radius: usize) -> Option<usize> {
    generate_candidate_indices(board, radius)
        .into_iter()
        .find(|&idx| move_wins(board, idx, stone))
}

fn move_wins(board: &Board, idx: usize, stone: i8) -> bool {
    if board.grid[idx] != EMPTY {
        return false;
    }
    let (row, col) = board.row_col(idx);
    for (row_step, col_step) in DIRECTIONS {
        let total = 1
            + board.count_direction(row, col, row_step, col_step, stone)
            + board.count_direction(row, col, -row_step, -col_step, stone);
        if total >= board.win_length {
            return true;
        }
    }
    false
}

fn ordered_candidates_from(
    board: &Board,
    stone: i8,
    candidates: Vec<usize>,
    limit: Option<usize>,
    preferred_move: Option<usize>,
) -> Vec<usize> {
    let mut scored = Vec::with_capacity(candidates.len());
    for idx in candidates {
        if board.grid[idx] != EMPTY {
            continue;
        }
        let (mut score, tactical) = candidate_analysis(board, idx, stone);
        if preferred_move == Some(idx) {
            score += WIN_SCORE * 2;
        }
        let (row, col) = board.row_col(idx);
        scored.push((score, row, col, idx, tactical));
    }

    scored.sort_by(|left, right| {
        right
            .0
            .cmp(&left.0)
            .then_with(|| right.1.cmp(&left.1))
            .then_with(|| right.2.cmp(&left.2))
    });

    let mut selected = Vec::with_capacity(scored.len());
    for (_score, _row, _col, idx, tactical) in scored {
        let is_within_limit = limit.map(|value| selected.len() < value).unwrap_or(true);
        if is_within_limit || tactical {
            selected.push(idx);
        }
    }
    selected
}

fn candidate_analysis(board: &Board, idx: usize, stone: i8) -> (i64, bool) {
    if move_wins(board, idx, stone) {
        return (WIN_SCORE, true);
    }

    let other = opponent(stone);
    if move_wins(board, idx, other) {
        return (WIN_SCORE - 1, true);
    }

    let (row, col) = board.row_col(idx);
    let center = (board.size - 1) as f64 / 2.0;
    let center_bonus =
        ((board.size as f64 - (center - row as f64).abs() - (center - col as f64).abs()) * 10.0)
            as i64;
    let own = move_analysis_after_move(board, idx, stone);
    let block = move_analysis_after_move(board, idx, other);
    let neighbor_bonus = neighbor_count(board, row, col, 2) as i64 * 20;
    let tactical = own.threats.four_threats() >= 1
        || block.threats.four_threats() >= 1
        || own.threats.is_forcing()
        || block.threats.is_forcing();
    (
        own.score * 2 + (block.score as f64 * 1.5) as i64 + center_bonus + neighbor_bonus,
        tactical,
    )
}

fn move_analysis_after_move(board: &Board, idx: usize, stone: i8) -> MoveAnalysis {
    if board.grid[idx] != EMPTY {
        return MoveAnalysis {
            score: 0,
            threats: Threats::default(),
        };
    }

    let (row, col) = board.row_col(idx);
    let mut score = 0;
    let mut threats = Threats::default();
    for (row_step, col_step) in DIRECTIONS {
        let line = line_through_move(board, row, col, row_step, col_step, stone);
        let analysis = analyze_line_v4(&line, stone);
        score += analysis.score;
        threats.open_fours += analysis.threats.open_fours;
        threats.fours += analysis.threats.fours;
        threats.open_threes += analysis.threats.open_threes;
        threats.threes += analysis.threats.threes;
    }

    MoveAnalysis {
        score: score + threat_bonus(threats),
        threats,
    }
}

fn line_through_move(
    board: &Board,
    row: usize,
    col: usize,
    row_step: isize,
    col_step: isize,
    stone: i8,
) -> Vec<i8> {
    let radius = board.win_length as isize + 1;
    let other = opponent(stone);
    let mut line = Vec::with_capacity((radius * 2 + 1) as usize);
    for offset in -radius..=radius {
        let current_row = row as isize + offset * row_step;
        let current_col = col as isize + offset * col_step;
        if offset == 0 {
            line.push(stone);
        } else if board.is_on_board(current_row, current_col) {
            line.push(board.grid[board.idx(current_row as usize, current_col as usize)]);
        } else {
            line.push(other);
        }
    }
    line
}

fn analyze_line_v4(line: &[i8], stone: i8) -> LineAnalysis {
    let text = line_to_pattern(line, stone);
    let win_count = count_pattern_occurrences(&text, &[b"XXXXX"]);
    let open_four_count = count_pattern_occurrences(&text, &OPEN_FOUR_PATTERNS);
    let four_count = count_pattern_occurrences(&text, &FOUR_PATTERNS);
    let open_three_count = count_pattern_occurrences(&text, &OPEN_THREE_PATTERNS);
    let three_count = count_pattern_occurrences(&text, &THREE_PATTERNS);
    let open_two_count = count_pattern_occurrences(&text, &OPEN_TWO_PATTERNS);

    let mut score = score_text_windows(&text).max(win_count * WIN_SCORE);
    score += open_four_count * OPEN_FOUR;
    score += four_count * FOUR;
    score += open_three_count * OPEN_THREE;
    score += three_count * THREE;
    score += open_two_count * OPEN_TWO;

    let has_open_four = open_four_count > 0;
    let has_four = four_count > 0 && !has_open_four;
    let has_open_three = open_three_count > 0 && !has_open_four && !has_four;
    let has_three = three_count > 0 && !has_open_four && !has_four && !has_open_three;

    LineAnalysis {
        score,
        threats: Threats {
            open_fours: i64::from(has_open_four),
            fours: i64::from(has_four),
            open_threes: i64::from(has_open_three),
            threes: i64::from(has_three),
        },
    }
}

fn score_text_windows(text: &[u8]) -> i64 {
    if text.len() < 5 {
        return 0;
    }

    let mut score = 0;
    for start in 0..=text.len() - 5 {
        let segment = &text[start..start + 5];
        if segment.contains(&b'O') {
            continue;
        }

        let own = segment.iter().filter(|&&value| value == b'X').count();
        let empty = segment.iter().filter(|&&value| value == b'.').count();
        if own == 5 {
            score += WIN_SCORE;
            continue;
        }

        let left_open = start > 0 && text[start - 1] == b'.';
        let right_open = start + 5 < text.len() && text[start + 5] == b'.';
        let open_ends = i32::from(left_open) + i32::from(right_open);

        if own == 4 && empty == 1 {
            score += if open_ends == 2 { OPEN_FOUR } else { FOUR };
        } else if own == 3 && empty == 2 {
            score += if open_ends == 2 { OPEN_THREE } else { THREE };
        } else if own == 2 && empty == 3 {
            score += if open_ends == 2 { OPEN_TWO } else { TWO };
        } else if own == 1 && empty == 4 {
            score += SINGLE;
        }
    }
    score
}

fn line_to_pattern(line: &[i8], stone: i8) -> Vec<u8> {
    let other = opponent(stone);
    line.iter()
        .map(|&value| {
            if value == stone {
                b'X'
            } else if value == EMPTY {
                b'.'
            } else if value == other {
                b'O'
            } else {
                b'O'
            }
        })
        .collect()
}

fn count_pattern_occurrences(text: &[u8], patterns: &[&[u8]]) -> i64 {
    let mut total = 0;
    for pattern in patterns {
        if pattern.is_empty() || text.len() < pattern.len() {
            continue;
        }
        for start in 0..=text.len() - pattern.len() {
            if &text[start..start + pattern.len()] == *pattern {
                total += 1;
            }
        }
    }
    total
}

fn threat_bonus(threats: Threats) -> i64 {
    let mut score = 0;
    if threats.has_double_four() {
        score += DOUBLE_FOUR;
    }
    if threats.has_four_three() {
        score += FOUR_THREE;
    }
    if threats.has_double_three() {
        score += DOUBLE_THREE;
    }
    score
}

fn neighbor_count(board: &Board, row: usize, col: usize, radius: usize) -> usize {
    let mut count = 0;
    for row_delta in -(radius as isize)..=(radius as isize) {
        for col_delta in -(radius as isize)..=(radius as isize) {
            if row_delta == 0 && col_delta == 0 {
                continue;
            }
            let next_row = row as isize + row_delta;
            let next_col = col as isize + col_delta;
            if board.is_on_board(next_row, next_col) {
                let idx = board.idx(next_row as usize, next_col as usize);
                if board.grid[idx] != EMPTY {
                    count += 1;
                }
            }
        }
    }
    count
}

fn static_score(board: &Board, stone: i8) -> i64 {
    let own = evaluate_for_v4(board, stone);
    let enemy = evaluate_for_v4(board, opponent(stone));
    own - (enemy as f64 * 1.16) as i64 + center_bias(board, stone)
}

fn evaluate_for_v4(board: &Board, stone: i8) -> i64 {
    let mut score = 0;
    let size = board.size;

    for row in 0..size {
        let mut line = Vec::with_capacity(size);
        for col in 0..size {
            line.push(board.grid[board.idx(row, col)]);
        }
        score += analyze_line_v4(&line, stone).score;
    }

    for col in 0..size {
        let mut line = Vec::with_capacity(size);
        for row in 0..size {
            line.push(board.grid[board.idx(row, col)]);
        }
        score += analyze_line_v4(&line, stone).score;
    }

    for start_col in 0..size {
        let mut line = Vec::new();
        let mut row = 0;
        let mut col = start_col;
        while row < size && col < size {
            line.push(board.grid[board.idx(row, col)]);
            row += 1;
            col += 1;
        }
        if line.len() >= board.win_length {
            score += analyze_line_v4(&line, stone).score;
        }
    }

    for start_row in 1..size {
        let mut line = Vec::new();
        let mut row = start_row;
        let mut col = 0;
        while row < size && col < size {
            line.push(board.grid[board.idx(row, col)]);
            row += 1;
            col += 1;
        }
        if line.len() >= board.win_length {
            score += analyze_line_v4(&line, stone).score;
        }
    }

    for start_col in 0..size {
        let mut line = Vec::new();
        let mut row = 0;
        let mut col = start_col as isize;
        while row < size && col >= 0 {
            line.push(board.grid[board.idx(row, col as usize)]);
            row += 1;
            col -= 1;
        }
        if line.len() >= board.win_length {
            score += analyze_line_v4(&line, stone).score;
        }
    }

    for start_row in 1..size {
        let mut line = Vec::new();
        let mut row = start_row;
        let mut col = size as isize - 1;
        while row < size && col >= 0 {
            line.push(board.grid[board.idx(row, col as usize)]);
            row += 1;
            col -= 1;
        }
        if line.len() >= board.win_length {
            score += analyze_line_v4(&line, stone).score;
        }
    }

    score
}

fn center_bias(board: &Board, stone: i8) -> i64 {
    let center = (board.size - 1) as f64 / 2.0;
    let mut score = 0;
    for (idx, &value) in board.grid.iter().enumerate() {
        if value == EMPTY {
            continue;
        }
        let (row, col) = board.row_col(idx);
        let distance = (center - row as f64).abs() + (center - col as f64).abs();
        let bias = ((board.size as f64 - distance) * 3.0) as i64;
        if value == stone {
            score += bias;
        } else {
            score -= bias;
        }
    }
    score
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn first_move_is_center() {
        let result =
            choose_move_v5_flat(vec![0; 15 * 15], 15, 5, BLACK, 2, 2, 18, 20260521).expect("move");

        assert_eq!((result.row, result.col), (7, 7));
    }

    #[test]
    fn finds_one_move_win() {
        let mut grid = vec![0; 15 * 15];
        for col in 3..7 {
            grid[7 * 15 + col] = BLACK;
        }

        let result = choose_move_v5_flat(grid, 15, 5, BLACK, 2, 2, 18, 20260521).expect("move");

        assert!([(7, 2), (7, 7)].contains(&(result.row, result.col)));
    }
}
