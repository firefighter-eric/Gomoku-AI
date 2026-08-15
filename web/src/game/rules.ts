export const EMPTY = 0 as const;
export const BLACK = 1 as const;
export const WHITE = -1 as const;
export const DRAW = 2 as const;
export const BOARD_SIZE = 15;
export const WIN_LENGTH = 5;

export type Stone = typeof BLACK | typeof WHITE;
export type Cell = typeof EMPTY | Stone;
export type Winner = Stone | typeof DRAW | null;

export interface Move {
  row: number;
  col: number;
  stone: Stone;
}

export function opponent(stone: Stone): Stone {
  return stone === BLACK ? WHITE : BLACK;
}

export function boardIndex(row: number, col: number, size = BOARD_SIZE): number {
  return row * size + col;
}

export function emptyBoard(size = BOARD_SIZE): Cell[] {
  return Array<Cell>(size * size).fill(EMPTY);
}

export function isOnBoard(row: number, col: number, size = BOARD_SIZE): boolean {
  return row >= 0 && col >= 0 && row < size && col < size;
}

export function winnerFrom(
  board: readonly Cell[],
  row: number,
  col: number,
  size = BOARD_SIZE,
  winLength = WIN_LENGTH,
): Winner {
  const stone = board[boardIndex(row, col, size)];
  if (stone !== BLACK && stone !== WHITE) {
    return null;
  }

  const directions = [
    [0, 1],
    [1, 0],
    [1, 1],
    [1, -1],
  ] as const;

  for (const [rowStep, colStep] of directions) {
    let count = 1;
    count += countDirection(board, row, col, rowStep, colStep, stone, size);
    count += countDirection(board, row, col, -rowStep, -colStep, stone, size);
    if (count >= winLength) {
      return stone;
    }
  }

  return board.every((cell) => cell !== EMPTY) ? DRAW : null;
}

function countDirection(
  board: readonly Cell[],
  row: number,
  col: number,
  rowStep: number,
  colStep: number,
  stone: Stone,
  size: number,
): number {
  let count = 0;
  let nextRow = row + rowStep;
  let nextCol = col + colStep;
  while (
    isOnBoard(nextRow, nextCol, size) &&
    board[boardIndex(nextRow, nextCol, size)] === stone
  ) {
    count += 1;
    nextRow += rowStep;
    nextCol += colStep;
  }
  return count;
}

export function formatMove(row: number, col: number): string {
  return `${columnLabel(col)}${row + 1}`;
}

export function columnLabel(index: number): string {
  let value = index;
  let label = "";
  while (value >= 0) {
    label = String.fromCharCode(65 + (value % 26)) + label;
    value = Math.floor(value / 26) - 1;
  }
  return label;
}

export function chooseFallbackMove(
  board: readonly Cell[],
  stone: Stone,
  size = BOARD_SIZE,
): [number, number] {
  const emptyMoves: Array<[number, number]> = [];
  const center = (size - 1) / 2;

  for (let row = 0; row < size; row += 1) {
    for (let col = 0; col < size; col += 1) {
      const index = boardIndex(row, col, size);
      if (board[index] !== EMPTY) {
        continue;
      }
      emptyMoves.push([row, col]);

      const ownBoard = [...board] as Cell[];
      ownBoard[index] = stone;
      if (winnerFrom(ownBoard, row, col, size) === stone) {
        return [row, col];
      }
    }
  }

  const other = opponent(stone);
  for (const [row, col] of emptyMoves) {
    const blockedBoard = [...board] as Cell[];
    blockedBoard[boardIndex(row, col, size)] = other;
    if (winnerFrom(blockedBoard, row, col, size) === other) {
      return [row, col];
    }
  }

  emptyMoves.sort((first, second) => {
    const firstScore = neighborhoodScore(board, first[0], first[1], size) * 100 -
      Math.abs(first[0] - center) - Math.abs(first[1] - center);
    const secondScore = neighborhoodScore(board, second[0], second[1], size) * 100 -
      Math.abs(second[0] - center) - Math.abs(second[1] - center);
    return secondScore - firstScore;
  });

  return emptyMoves[0] ?? [Math.floor(center), Math.floor(center)];
}

function neighborhoodScore(
  board: readonly Cell[],
  row: number,
  col: number,
  size: number,
): number {
  let score = 0;
  for (let rowDelta = -2; rowDelta <= 2; rowDelta += 1) {
    for (let colDelta = -2; colDelta <= 2; colDelta += 1) {
      if (rowDelta === 0 && colDelta === 0) {
        continue;
      }
      const nextRow = row + rowDelta;
      const nextCol = col + colDelta;
      if (isOnBoard(nextRow, nextCol, size) && board[boardIndex(nextRow, nextCol, size)] !== EMPTY) {
        score += Math.max(1, 3 - Math.max(Math.abs(rowDelta), Math.abs(colDelta)));
      }
    }
  }
  return score;
}
