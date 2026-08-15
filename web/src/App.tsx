import { useEffect, useReducer, useRef } from "react";

import { playEnabledSound, playMoveSound, playOutcomeSound, unlockSound } from "./audio/sound";
import { Board } from "./components/Board";
import { BrandMark } from "./components/BrandMark";
import { Controls } from "./components/Controls";
import { InfoDialog } from "./components/InfoDialog";
import { SoundToggle } from "./components/SoundToggle";
import { BOARD_SIZE, WIN_LENGTH, chooseFallbackMove, type Stone } from "./game/rules";
import {
  canHumanPlay,
  createGameState,
  gameReducer,
  isAiTurn,
  statusCopy,
  type GameMode,
} from "./game/state";
import type { AiRequest, AiResponse } from "./workers/messages";

const SETTINGS_KEY = "gomoku-ai.web.settings.v1";

function initialState() {
  try {
    const saved = JSON.parse(localStorage.getItem(SETTINGS_KEY) ?? "null") as {
      mode?: GameMode;
      humanStone?: Stone;
      depth?: number;
      soundEnabled?: boolean;
    } | null;
    if (!saved) {
      return createGameState();
    }
    return createGameState({
      mode: saved.mode === "ai-ai" || saved.mode === "human-human" ? saved.mode : "human-ai",
      humanStone: saved.humanStone === -1 ? -1 : 1,
      depth: typeof saved.depth === "number" ? Math.min(10, Math.max(1, saved.depth)) : 5,
      soundEnabled: saved.soundEnabled !== false,
    });
  } catch {
    return createGameState();
  }
}

export default function App() {
  const [state, dispatch] = useReducer(gameReducer, undefined, initialState);
  const workerRef = useRef<Worker | null>(null);
  const pendingRef = useRef<number | null>(null);
  const requestCounterRef = useRef(0);
  const stateRef = useRef(state);
  const previousMoveCountRef = useRef(state.moves.length);
  const previousWinnerRef = useRef(state.winner);

  function ensureWorker() {
    if (workerRef.current) {
      return workerRef.current;
    }
    const worker = new Worker(new URL("./workers/ai.worker.ts", import.meta.url), { type: "module" });
    worker.onmessage = (event: MessageEvent<AiResponse>) => {
      const response = event.data;
      if (response.type !== "move" || response.requestId !== pendingRef.current) {
        return;
      }
      pendingRef.current = null;
      const snapshot = stateRef.current;
      dispatch({ type: "backend", value: response.backend });
      dispatch({
        type: "play",
        row: response.row,
        col: response.col,
        expectedMoveCount: snapshot.moves.length,
        expectedStone: snapshot.current,
      });
    };
    worker.onerror = () => {
      pendingRef.current = null;
      worker.terminate();
      workerRef.current = null;
      const snapshot = stateRef.current;
      const [row, col] = chooseFallbackMove(snapshot.board, snapshot.current);
      dispatch({ type: "backend", value: "fallback" });
      dispatch({
        type: "play",
        row,
        col,
        expectedMoveCount: snapshot.moves.length,
        expectedStone: snapshot.current,
      });
    };
    workerRef.current = worker;
    return worker;
  }

  function cancelAi() {
    workerRef.current?.terminate();
    workerRef.current = null;
    pendingRef.current = null;
  }

  useEffect(() => {
    stateRef.current = state;
  }, [state]);

  useEffect(() => {
    try {
      localStorage.setItem(SETTINGS_KEY, JSON.stringify({
        mode: state.mode,
        humanStone: state.humanStone,
        depth: state.depth,
        soundEnabled: state.soundEnabled,
      }));
    } catch {
      // The game remains playable when storage is disabled or full.
    }
  }, [state.depth, state.humanStone, state.mode, state.soundEnabled]);

  useEffect(() => {
    if (state.soundEnabled && state.moves.length === previousMoveCountRef.current + 1) {
      const latestMove = state.moves.at(-1);
      if (latestMove) {
        playMoveSound(latestMove.stone);
      }
    }
    if (state.soundEnabled && previousWinnerRef.current === null && state.winner !== null) {
      playOutcomeSound(state.winner);
    }
    previousMoveCountRef.current = state.moves.length;
    previousWinnerRef.current = state.winner;
  }, [state.moves, state.soundEnabled, state.winner]);

  useEffect(() => {
    if (!isAiTurn(state) || pendingRef.current !== null) {
      return;
    }
    const requestId = requestCounterRef.current + 1;
    requestCounterRef.current = requestId;
    pendingRef.current = requestId;
    dispatch({ type: "thinking", value: true });

    const request: AiRequest = {
      type: "choose-move",
      requestId,
      grid: [...state.board],
      size: BOARD_SIZE,
      winLength: WIN_LENGTH,
      stone: state.current,
      depth: state.depth,
      candidateRadius: 2,
      candidateLimit: 18,
      seed: 20260521,
    };
    ensureWorker().postMessage(request);
  }, [state]);

  useEffect(() => () => {
    workerRef.current?.terminate();
    workerRef.current = null;
    pendingRef.current = null;
  }, []);

  const status = statusCopy(state);

  function handlePlay(row: number, col: number) {
    if (canHumanPlay(state)) {
      if (state.soundEnabled) {
        unlockSound();
      }
      dispatch({ type: "play", row, col });
    }
  }

  function changeMode(mode: GameMode) {
    if (mode !== state.mode) {
      if (state.soundEnabled) {
        unlockSound();
      }
      cancelAi();
      dispatch({ type: "mode", value: mode });
    }
  }

  function changeHumanStone(stone: Stone) {
    if (stone !== state.humanStone) {
      if (state.soundEnabled) {
        unlockSound();
      }
      cancelAi();
      dispatch({ type: "human-stone", value: stone });
    }
  }

  function restart() {
    cancelAi();
    dispatch({ type: "restart" });
  }

  function undo() {
    cancelAi();
    dispatch({ type: "undo" });
  }

  function toggleSound() {
    const enabled = !state.soundEnabled;
    if (enabled) {
      unlockSound();
      playEnabledSound();
    }
    dispatch({ type: "sound-enabled", value: enabled });
  }

  return (
    <div className="app-shell">
      <header className="app-header">
        <a className="brand" href="/" aria-label="Gomoku-AI 首页">
          <BrandMark />
          <span className="brand__name">Gomoku-AI</span>
          <span className="brand__descriptor">五子棋</span>
        </a>
        <div className="header-actions">
          <SoundToggle enabled={state.soundEnabled} onToggle={toggleSound} />
          <InfoDialog />
        </div>
      </header>

      <main className="game-layout">
        <section className="game-stage" aria-labelledby="game-status">
          <div className="game-status" aria-live="polite">
            <div>
              <span className={`thinking-mark${state.aiThinking ? " is-active" : ""}`} aria-hidden="true" />
              <h1 id="game-status">{status.title}</h1>
            </div>
            <p>{status.detail}</p>
          </div>
          <Board board={state.board} disabled={!canHumanPlay(state)} moves={state.moves} onPlay={handlePlay} />
        </section>

        <Controls
          state={state}
          onDepthChange={(depth) => dispatch({ type: "depth", value: depth })}
          onHumanStoneChange={changeHumanStone}
          onModeChange={changeMode}
          onRestart={restart}
          onUndo={undo}
        />
      </main>
    </div>
  );
}
