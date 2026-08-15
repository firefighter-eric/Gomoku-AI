import { describe, expect, it } from "vitest";

import {
  BLACK,
  BOARD_SIZE,
  EMPTY,
  WHITE,
  boardIndex,
  chooseFallbackMove,
  emptyBoard,
  formatMove,
  winnerFrom,
} from "../src/game/rules";

describe("game rules", () => {
  it("formats board coordinates consistently with the Python game", () => {
    expect(formatMove(0, 0)).toBe("A1");
    expect(formatMove(7, 7)).toBe("H8");
    expect(formatMove(14, 14)).toBe("O15");
  });

  it("detects five or more stones in every direction", () => {
    const scenarios = [
      [0, 1],
      [1, 0],
      [1, 1],
      [1, -1],
    ] as const;

    for (const [rowStep, colStep] of scenarios) {
      const board = emptyBoard();
      for (let offset = 0; offset < 6; offset += 1) {
        const row = colStep < 0 ? 7 + offset * rowStep : 3 + offset * rowStep;
        const col = colStep < 0 ? 10 + offset * colStep : 3 + offset * colStep;
        board[boardIndex(row, col)] = BLACK;
      }
      const row = colStep < 0 ? 7 + 5 * rowStep : 3 + 5 * rowStep;
      const col = colStep < 0 ? 10 + 5 * colStep : 3 + 5 * colStep;
      expect(winnerFrom(board, row, col)).toBe(BLACK);
    }
  });

  it("ignores an empty intersection", () => {
    expect(winnerFrom(emptyBoard(), 7, 7)).toBeNull();
  });
});

describe("fallback AI", () => {
  it("opens in the center", () => {
    expect(chooseFallbackMove(emptyBoard(), BLACK)).toEqual([7, 7]);
  });

  it("takes an immediate winning move", () => {
    const board = emptyBoard();
    for (let col = 4; col < 8; col += 1) {
      board[boardIndex(7, col)] = WHITE;
    }
    expect(chooseFallbackMove(board, WHITE)).toEqual([7, 3]);
  });

  it("blocks an opponent's immediate win", () => {
    const board = Array(BOARD_SIZE * BOARD_SIZE).fill(EMPTY);
    for (let row = 4; row < 8; row += 1) {
      board[boardIndex(row, 7)] = WHITE;
    }
    expect(chooseFallbackMove(board, BLACK)).toEqual([3, 7]);
  });
});
