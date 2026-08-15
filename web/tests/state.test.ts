import { describe, expect, it } from "vitest";

import { BLACK, EMPTY, WHITE, boardIndex } from "../src/game/rules";
import {
  canHumanPlay,
  createGameState,
  gameReducer,
  isAiTurn,
  statusCopy,
} from "../src/game/state";

describe("game state", () => {
  it("routes turns between the human and AI", () => {
    let state = createGameState();
    expect(canHumanPlay(state)).toBe(true);
    state = gameReducer(state, { type: "play", row: 7, col: 7 });
    expect(state.current).toBe(WHITE);
    expect(isAiTurn(state)).toBe(true);
  });

  it("starts with an AI turn when the human chooses white", () => {
    const state = gameReducer(createGameState(), { type: "human-stone", value: WHITE });
    expect(state.current).toBe(BLACK);
    expect(isAiTurn(state)).toBe(true);
    expect(statusCopy(state).title).toBe("AI 正在思考");
  });

  it("undoes the latest human move together with the AI reply", () => {
    let state = createGameState();
    state = gameReducer(state, { type: "play", row: 7, col: 7 });
    state = gameReducer(state, { type: "play", row: 7, col: 8 });
    state = gameReducer(state, { type: "play", row: 8, col: 7 });
    state = gameReducer(state, { type: "play", row: 6, col: 7 });
    state = gameReducer(state, { type: "undo" });

    expect(state.moves).toHaveLength(2);
    expect(state.current).toBe(BLACK);
    expect(state.board[boardIndex(8, 7)]).toBe(EMPTY);
    expect(state.board[boardIndex(6, 7)]).toBe(EMPTY);
  });

  it("rejects stale worker responses", () => {
    const state = gameReducer(createGameState(), {
      type: "play",
      row: 4,
      col: 4,
      expectedMoveCount: 2,
      expectedStone: BLACK,
    });
    expect(state.moves).toHaveLength(0);
  });

  it("restarts when the mode changes", () => {
    let state = createGameState();
    state = gameReducer(state, { type: "play", row: 7, col: 7 });
    state = gameReducer(state, { type: "mode", value: "ai-ai" });
    expect(state.mode).toBe("ai-ai");
    expect(state.moves).toHaveLength(0);
    expect(state.current).toBe(BLACK);
  });

  it("supports two local human players without invoking the AI", () => {
    let state = gameReducer(createGameState(), { type: "mode", value: "human-human" });
    expect(canHumanPlay(state)).toBe(true);
    expect(isAiTurn(state)).toBe(false);
    expect(statusCopy(state).title).toBe("黑棋回合");

    state = gameReducer(state, { type: "play", row: 7, col: 7 });
    expect(state.current).toBe(WHITE);
    expect(canHumanPlay(state)).toBe(true);
    expect(statusCopy(state).title).toBe("白棋回合");

    state = gameReducer(state, { type: "undo" });
    expect(state.moves).toHaveLength(0);
    expect(state.current).toBe(BLACK);
  });
});
