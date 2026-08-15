import {
  BLACK,
  BOARD_SIZE,
  DRAW,
  EMPTY,
  WHITE,
  boardIndex,
  emptyBoard,
  opponent,
  winnerFrom,
  type Cell,
  type Move,
  type Stone,
  type Winner,
} from "./rules";

export type GameMode = "human-ai" | "human-human" | "ai-ai";
export type EngineBackend = "wasm" | "fallback" | "loading";

export interface GameState {
  board: Cell[];
  moves: Move[];
  current: Stone;
  winner: Winner;
  mode: GameMode;
  humanStone: Stone;
  depth: number;
  aiThinking: boolean;
  backend: EngineBackend;
  soundEnabled: boolean;
  generation: number;
}

export type GameAction =
  | { type: "play"; row: number; col: number; expectedMoveCount?: number; expectedStone?: Stone }
  | { type: "thinking"; value: boolean }
  | { type: "backend"; value: Exclude<EngineBackend, "loading"> }
  | { type: "sound-enabled"; value: boolean }
  | { type: "mode"; value: GameMode }
  | { type: "human-stone"; value: Stone }
  | { type: "depth"; value: number }
  | { type: "restart" }
  | { type: "undo" };

export function createGameState(overrides: Partial<GameState> = {}): GameState {
  return {
    board: emptyBoard(),
    moves: [],
    current: BLACK,
    winner: null,
    mode: "human-ai",
    humanStone: BLACK,
    depth: 5,
    aiThinking: false,
    backend: "loading",
    soundEnabled: true,
    generation: 0,
    ...overrides,
  };
}

export function gameReducer(state: GameState, action: GameAction): GameState {
  switch (action.type) {
    case "play":
      return play(state, action);
    case "thinking":
      return { ...state, aiThinking: action.value };
    case "backend":
      return { ...state, backend: action.value };
    case "sound-enabled":
      return { ...state, soundEnabled: action.value };
    case "depth":
      return { ...state, depth: Math.min(10, Math.max(1, action.value)) };
    case "mode":
      return restart({ ...state, mode: action.value });
    case "human-stone":
      return restart({ ...state, humanStone: action.value });
    case "restart":
      return restart(state);
    case "undo":
      return undo(state);
  }
}

function play(
  state: GameState,
  action: Extract<GameAction, { type: "play" }>,
): GameState {
  if (
    state.winner !== null ||
    action.row < 0 ||
    action.col < 0 ||
    action.row >= BOARD_SIZE ||
    action.col >= BOARD_SIZE ||
    state.board[boardIndex(action.row, action.col)] !== EMPTY ||
    (action.expectedMoveCount !== undefined && action.expectedMoveCount !== state.moves.length) ||
    (action.expectedStone !== undefined && action.expectedStone !== state.current)
  ) {
    return { ...state, aiThinking: false };
  }

  const board = [...state.board];
  board[boardIndex(action.row, action.col)] = state.current;
  const moves = [...state.moves, { row: action.row, col: action.col, stone: state.current }];
  const winner = winnerFrom(board, action.row, action.col);

  return {
    ...state,
    board,
    moves,
    current: winner === null ? opponent(state.current) : state.current,
    winner,
    aiThinking: false,
  };
}

function restart(state: GameState): GameState {
  return {
    ...state,
    board: emptyBoard(),
    moves: [],
    current: BLACK,
    winner: null,
    aiThinking: false,
    generation: state.generation + 1,
  };
}

function undo(state: GameState): GameState {
  if (state.moves.length === 0) {
    return state;
  }

  let remaining: Move[];
  if (state.mode === "human-ai") {
    let lastHumanIndex = -1;
    for (let index = state.moves.length - 1; index >= 0; index -= 1) {
      if (state.moves[index].stone === state.humanStone) {
        lastHumanIndex = index;
        break;
      }
    }
    if (lastHumanIndex < 0) {
      return state;
    }
    remaining = state.moves.slice(0, lastHumanIndex);
  } else {
    remaining = state.moves.slice(0, -1);
  }

  const board = emptyBoard();
  for (const move of remaining) {
    board[boardIndex(move.row, move.col)] = move.stone;
  }

  return {
    ...state,
    board,
    moves: remaining,
    current: remaining.length % 2 === 0 ? BLACK : WHITE,
    winner: null,
    aiThinking: false,
    generation: state.generation + 1,
  };
}

export function isAiTurn(state: GameState): boolean {
  return state.winner === null && (
    state.mode === "ai-ai" ||
    (state.mode === "human-ai" && state.current !== state.humanStone)
  );
}

export function canHumanPlay(state: GameState): boolean {
  return state.mode !== "ai-ai" && !isAiTurn(state) && state.winner === null && !state.aiThinking;
}

export function canUndo(state: GameState): boolean {
  if (state.aiThinking) {
    return false;
  }
  return state.mode === "human-ai"
    ? state.moves.some((move) => move.stone === state.humanStone)
    : state.moves.length > 0;
}

export function statusCopy(state: GameState): { title: string; detail: string } {
  if (state.winner === DRAW) {
    return { title: "和棋", detail: `共 ${state.moves.length} 手` };
  }
  if (state.winner === BLACK || state.winner === WHITE) {
    const stoneName = state.winner === BLACK ? "黑棋" : "白棋";
    if (state.mode === "human-human") {
      return { title: `${stoneName}胜出`, detail: `双人对战 · 共 ${state.moves.length} 手` };
    }
    const isHumanWinner = state.mode === "human-ai" && state.winner === state.humanStone;
    return {
      title: state.mode === "human-ai" ? (isHumanWinner ? "你赢了" : "AI 胜出") : `${stoneName}胜出`,
      detail: `${stoneName} · 共 ${state.moves.length} 手`,
    };
  }
  if (state.aiThinking || isAiTurn(state)) {
    const stoneName = state.current === BLACK ? "黑棋" : "白棋";
    return {
      title: state.mode === "human-ai" ? "AI 正在思考" : `${stoneName}思考中`,
      detail: `${stoneName} · 第 ${state.moves.length + 1} 手`,
    };
  }
  if (state.mode === "human-human") {
    const stoneName = state.current === BLACK ? "黑棋" : "白棋";
    return { title: `${stoneName}回合`, detail: `双人对战 · 第 ${state.moves.length + 1} 手` };
  }
  return {
    title: "你的回合",
    detail: `执${state.humanStone === BLACK ? "黑" : "白"} · 第 ${state.moves.length + 1} 手`,
  };
}
