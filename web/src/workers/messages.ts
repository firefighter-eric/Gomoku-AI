import type { Cell, Stone } from "../game/rules";

export interface AiRequest {
  type: "choose-move";
  requestId: number;
  grid: Cell[];
  size: number;
  winLength: number;
  stone: Stone;
  depth: number;
  candidateRadius: number;
  candidateLimit: number;
  seed: number;
}

export interface AiResponse {
  type: "move";
  requestId: number;
  row: number;
  col: number;
  backend: "wasm" | "fallback";
  error?: string;
}
