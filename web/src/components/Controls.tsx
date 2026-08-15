import { useEffect, useState, type CSSProperties } from "react";

import { BLACK, WHITE, formatMove, type Stone } from "../game/rules";
import { canUndo, statusCopy, type EngineBackend, type GameMode, type GameState } from "../game/state";
import { ChevronIcon } from "./BrandMark";

interface ControlsProps {
  state: GameState;
  onModeChange: (mode: GameMode) => void;
  onHumanStoneChange: (stone: Stone) => void;
  onDepthChange: (depth: number) => void;
  onUndo: () => void;
  onRestart: () => void;
}

function backendCopy(backend: EngineBackend) {
  if (backend === "wasm") {
    return "Rust · WebAssembly";
  }
  if (backend === "fallback") {
    return "浏览器兼容引擎";
  }
  return "正在载入 Rust 引擎";
}

export function Controls({
  state,
  onModeChange,
  onHumanStoneChange,
  onDepthChange,
  onUndo,
  onRestart,
}: ControlsProps) {
  const recentMoves = [...state.moves].reverse().slice(0, 8);
  const status = statusCopy(state);
  const [historyOpen, setHistoryOpen] = useState(() => (
    typeof window.matchMedia !== "function" || window.matchMedia("(min-width: 901px)").matches
  ));

  useEffect(() => {
    if (typeof window.matchMedia !== "function") {
      return undefined;
    }

    const desktopQuery = window.matchMedia("(min-width: 901px)");
    const syncHistory = (event: MediaQueryListEvent) => setHistoryOpen(event.matches);
    desktopQuery.addEventListener("change", syncHistory);
    return () => desktopQuery.removeEventListener("change", syncHistory);
  }, []);

  return (
    <aside className="controls" aria-label="对局设置">
      <div className="game-status desktop-status" aria-live="polite">
        <div>
          <span className={`thinking-mark${state.aiThinking ? " is-active" : ""}`} aria-hidden="true" />
          <h2>{status.title}</h2>
        </div>
        <p>{status.detail}</p>
      </div>

      <div className="controls__primary-actions mobile-actions">
        <button className="button button--secondary" disabled={!canUndo(state)} onClick={onUndo} type="button">
          悔棋
        </button>
        <button className="button button--primary" onClick={onRestart} type="button">
          重新开始
        </button>
      </div>

      <div className="control-group">
        <span className="control-label" id="mode-label">对局模式</span>
        <div className="segmented" aria-labelledby="mode-label">
          <button
            aria-pressed={state.mode === "human-ai"}
            className={state.mode === "human-ai" ? "is-selected" : ""}
            onClick={() => onModeChange("human-ai")}
            type="button"
          >
            人机对战
          </button>
          <button
            aria-pressed={state.mode === "human-human"}
            className={state.mode === "human-human" ? "is-selected" : ""}
            onClick={() => onModeChange("human-human")}
            type="button"
          >
            双人对战
          </button>
          <button
            aria-pressed={state.mode === "ai-ai"}
            className={state.mode === "ai-ai" ? "is-selected" : ""}
            onClick={() => onModeChange("ai-ai")}
            type="button"
          >
            AI 对 AI
          </button>
        </div>
      </div>

      <div className="control-group">
        <span className="control-label" id="stone-label">执子</span>
        <div className="stone-choice" aria-labelledby="stone-label">
          <button
            aria-pressed={state.humanStone === BLACK}
            className={state.humanStone === BLACK ? "is-selected" : ""}
            disabled={state.mode !== "human-ai"}
            onClick={() => onHumanStoneChange(BLACK)}
            type="button"
          >
            <span className="mini-stone mini-stone--black" aria-hidden="true" />黑棋
          </button>
          <button
            aria-pressed={state.humanStone === WHITE}
            className={state.humanStone === WHITE ? "is-selected" : ""}
            disabled={state.mode !== "human-ai"}
            onClick={() => onHumanStoneChange(WHITE)}
            type="button"
          >
            <span className="mini-stone mini-stone--white" aria-hidden="true" />白棋
          </button>
        </div>
      </div>

      <label className="control-group">
        <span className="control-label">AI 算法</span>
        <span className="select-wrap">
          <select aria-label="AI 算法" defaultValue="v5" disabled={state.mode === "human-human"}>
            <option value="v5">Alpha-Beta v5</option>
          </select>
          <ChevronIcon />
        </span>
      </label>

      <label className="control-group difficulty">
        <span className="difficulty__heading">
          <span className="control-label">难度</span>
          <strong>{state.depth}</strong>
        </span>
        <input
          aria-label="AI 难度"
          max="10"
          min="1"
          disabled={state.mode === "human-human"}
          onChange={(event) => onDepthChange(Number(event.target.value))}
          style={{ "--range-progress": `${((state.depth - 1) / 9) * 100}%` } as CSSProperties}
          type="range"
          value={state.depth}
        />
        <span className="difficulty__ticks" aria-hidden="true">
          {Array.from({ length: 10 }, (_, index) => <span key={index}>{index + 1}</span>)}
        </span>
      </label>

      <div className="controls__primary-actions desktop-actions">
        <button className="button button--secondary" disabled={!canUndo(state)} onClick={onUndo} type="button">
          悔棋
        </button>
        <button className="button button--primary" onClick={onRestart} type="button">
          重新开始
        </button>
      </div>

      <details
        className="move-history"
        onToggle={(event) => setHistoryOpen(event.currentTarget.open)}
        open={historyOpen}
      >
        <summary>
          <span>着法记录<span className="move-history__count"> · {state.moves.length} 手</span></span>
          <ChevronIcon />
        </summary>
        <ol aria-label="着法记录">
          {recentMoves.length === 0 ? (
            <li className="move-history__empty">落子后将在这里显示记录</li>
          ) : recentMoves.map((move, index) => (
            <li className={index === 0 ? "is-latest" : ""} key={`${state.moves.length - index}-${move.row}-${move.col}`}>
              <span className={`mini-stone mini-stone--${move.stone === BLACK ? "black" : "white"}`} aria-hidden="true" />
              <span>{state.moves.length - index}.</span>
              <strong>{formatMove(move.row, move.col)}</strong>
            </li>
          ))}
        </ol>
      </details>

      <div className="engine-note">
        <span className={`engine-dot engine-dot--${state.backend}`} aria-hidden="true" />
        <p><strong>{backendCopy(state.backend)}</strong><br />所有计算均在浏览器本地完成</p>
      </div>
    </aside>
  );
}
