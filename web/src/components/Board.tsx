import { useMemo, useState, type KeyboardEvent, type PointerEvent } from "react";

import {
  BLACK,
  BOARD_SIZE,
  EMPTY,
  WHITE,
  columnLabel,
  formatMove,
  type Cell,
  type Move,
} from "../game/rules";
import { BOARD_PADDING, GRID_SIZE, VIEWBOX_SIZE, pointToCell } from "../game/geometry";

interface BoardProps {
  board: readonly Cell[];
  moves: readonly Move[];
  disabled: boolean;
  onPlay: (row: number, col: number) => void;
}

export function Board({ board, moves, disabled, onPlay }: BoardProps) {
  const lastMove = moves.at(-1) ?? null;
  const [hovered, setHovered] = useState<{ row: number; col: number } | null>(null);
  const [cursor, setCursor] = useState({ row: 7, col: 7 });
  const step = GRID_SIZE / (BOARD_SIZE - 1);
  const lines = useMemo(() => Array.from({ length: BOARD_SIZE }, (_, index) => index), []);

  function cellFromPointer(event: PointerEvent<SVGSVGElement>) {
    const rect = event.currentTarget.getBoundingClientRect();
    const x = ((event.clientX - rect.left) / rect.width) * VIEWBOX_SIZE;
    const y = ((event.clientY - rect.top) / rect.height) * VIEWBOX_SIZE;
    return pointToCell(x, y);
  }

  function handlePointerMove(event: PointerEvent<SVGSVGElement>) {
    const cell = cellFromPointer(event);
    if (!cell || disabled || board[cell.row * BOARD_SIZE + cell.col] !== EMPTY) {
      setHovered(null);
      return;
    }
    setHovered(cell);
  }

  function handlePointerDown(event: PointerEvent<SVGSVGElement>) {
    const cell = cellFromPointer(event);
    if (!cell || disabled || board[cell.row * BOARD_SIZE + cell.col] !== EMPTY) {
      return;
    }
    setCursor(cell);
    onPlay(cell.row, cell.col);
  }

  function handleKeyDown(event: KeyboardEvent<SVGSVGElement>) {
    const movements: Record<string, [number, number]> = {
      ArrowUp: [-1, 0],
      ArrowDown: [1, 0],
      ArrowLeft: [0, -1],
      ArrowRight: [0, 1],
    };
    const movement = movements[event.key];
    if (movement) {
      event.preventDefault();
      setCursor(({ row, col }) => ({
        row: Math.min(BOARD_SIZE - 1, Math.max(0, row + movement[0])),
        col: Math.min(BOARD_SIZE - 1, Math.max(0, col + movement[1])),
      }));
      return;
    }
    if ((event.key === "Enter" || event.key === " ") && !disabled) {
      event.preventDefault();
      if (board[cursor.row * BOARD_SIZE + cursor.col] === EMPTY) {
        onPlay(cursor.row, cursor.col);
      }
    }
  }

  return (
    <div className={`board-shell${disabled ? " board-shell--disabled" : ""}`}>
      <svg
        className="board"
        viewBox={`0 0 ${VIEWBOX_SIZE} ${VIEWBOX_SIZE}`}
        role="grid"
        aria-label="十五路五子棋棋盘。使用方向键移动焦点，按空格或回车落子。"
        aria-disabled={disabled}
        tabIndex={0}
        onKeyDown={handleKeyDown}
        onPointerDown={handlePointerDown}
        onPointerLeave={() => setHovered(null)}
        onPointerMove={handlePointerMove}
      >
        <defs>
          <linearGradient id="board-surface" x1="0" x2="1" y1="0" y2="1">
            <stop offset="0" stopColor="#e7b76c" />
            <stop offset="0.46" stopColor="#e1aa5b" />
            <stop offset="1" stopColor="#d69a49" />
          </linearGradient>
          <radialGradient id="black-stone" cx="34%" cy="28%" r="68%">
            <stop offset="0" stopColor="#62615e" />
            <stop offset="0.34" stopColor="#20201f" />
            <stop offset="1" stopColor="#050505" />
          </radialGradient>
          <radialGradient id="white-stone" cx="34%" cy="28%" r="72%">
            <stop offset="0" stopColor="#ffffff" />
            <stop offset="0.7" stopColor="#f1efe8" />
            <stop offset="1" stopColor="#d5d1c6" />
          </radialGradient>
          <filter id="wood-grain" x="0" y="0" width="100%" height="100%">
            <feTurbulence baseFrequency="0.012 0.22" numOctaves="2" seed="8" type="fractalNoise" />
            <feColorMatrix values="0 0 0 0 0.36 0 0 0 0 0.19 0 0 0 0 0.04 0 0 0 .11 0" />
            <feBlend in="SourceGraphic" mode="multiply" />
          </filter>
          <filter id="stone-shadow" x="-30%" y="-30%" width="160%" height="170%">
            <feDropShadow dx="0" dy="3" floodColor="#3f2b12" floodOpacity="0.34" stdDeviation="2.2" />
          </filter>
        </defs>

        <rect className="board__frame" x="6" y="6" width="748" height="748" rx="7" />
        <rect className="board__surface" x="19" y="19" width="722" height="722" rx="2" filter="url(#wood-grain)" />

        {lines.map((index) => {
          const position = BOARD_PADDING + index * step;
          return (
            <g key={`line-${index}`}>
              <line className="board__grid-line" x1={BOARD_PADDING} x2={VIEWBOX_SIZE - BOARD_PADDING} y1={position} y2={position} />
              <line className="board__grid-line" x1={position} x2={position} y1={BOARD_PADDING} y2={VIEWBOX_SIZE - BOARD_PADDING} />
              <text className="board__coordinate" x={position} y="38" textAnchor="middle">{columnLabel(index)}</text>
              <text className="board__coordinate" x={position} y="739" textAnchor="middle">{columnLabel(index)}</text>
              <text className="board__coordinate" x="35" y={position + 5} textAnchor="middle">{index + 1}</text>
            </g>
          );
        })}

        {[3, 7, 11].flatMap((row) =>
          [3, 7, 11].map((col) => (
            <circle
              className="board__star"
              cx={BOARD_PADDING + col * step}
              cy={BOARD_PADDING + row * step}
              key={`star-${row}-${col}`}
              r="3.8"
            />
          )),
        )}

        {board.map((cell, index) => {
          if (cell !== BLACK && cell !== WHITE) {
            return null;
          }
          const row = Math.floor(index / BOARD_SIZE);
          const col = index % BOARD_SIZE;
          const x = BOARD_PADDING + col * step;
          const y = BOARD_PADDING + row * step;
          const isLast = lastMove?.row === row && lastMove.col === col;
          return (
            <g key={`stone-${row}-${col}`} aria-label={`${formatMove(row, col)} ${cell === BLACK ? "黑棋" : "白棋"}`}>
              <circle
                cx={x}
                cy={y}
                r={step * 0.39}
                fill={cell === BLACK ? "url(#black-stone)" : "url(#white-stone)"}
                filter="url(#stone-shadow)"
                stroke={cell === WHITE ? "#aaa59a" : "#050505"}
                strokeWidth="0.9"
              />
              {isLast && <circle className="board__last-move" cx={x} cy={y} r={step * 0.46} />}
            </g>
          );
        })}

        {hovered && (
          <circle
            className="board__hover"
            cx={BOARD_PADDING + hovered.col * step}
            cy={BOARD_PADDING + hovered.row * step}
            r={step * 0.28}
          />
        )}
        <path
          className="board__keyboard-cursor"
          d={`M ${BOARD_PADDING + cursor.col * step - 9} ${BOARD_PADDING + cursor.row * step - 15} h -6 v 6 M ${BOARD_PADDING + cursor.col * step + 9} ${BOARD_PADDING + cursor.row * step - 15} h 6 v 6 M ${BOARD_PADDING + cursor.col * step - 9} ${BOARD_PADDING + cursor.row * step + 15} h -6 v -6 M ${BOARD_PADDING + cursor.col * step + 9} ${BOARD_PADDING + cursor.row * step + 15} h 6 v -6`}
        />
      </svg>
    </div>
  );
}
