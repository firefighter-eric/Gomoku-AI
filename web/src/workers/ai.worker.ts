/// <reference lib="webworker" />

import { chooseFallbackMove } from "../game/rules";
import type { AiRequest, AiResponse } from "./messages";

interface WasmEngine {
  default: () => Promise<unknown>;
  choose_move_v5: (
    grid: Int8Array,
    size: number,
    winLength: number,
    stone: number,
    depth: number,
    candidateRadius: number,
    candidateLimit: number,
    seed: bigint,
  ) => Uint32Array;
}

let enginePromise: Promise<WasmEngine> | null = null;

async function loadEngine(): Promise<WasmEngine> {
  if (!enginePromise) {
    enginePromise = import("../wasm/pkg/gomoku_ai_wasm.js").then(async (module) => {
      const engine = module as unknown as WasmEngine;
      await engine.default();
      return engine;
    });
  }
  return enginePromise;
}

self.onmessage = async (event: MessageEvent<AiRequest>) => {
  const request = event.data;
  if (request.type !== "choose-move") {
    return;
  }

  let response: AiResponse;
  try {
    const engine = await loadEngine();
    const result = engine.choose_move_v5(
      Int8Array.from(request.grid),
      request.size,
      request.winLength,
      request.stone,
      request.depth,
      request.candidateRadius,
      request.candidateLimit,
      BigInt(request.seed),
    );
    response = {
      type: "move",
      requestId: request.requestId,
      row: result[0],
      col: result[1],
      backend: "wasm",
    };
  } catch (error) {
    const [row, col] = chooseFallbackMove(request.grid, request.stone, request.size);
    response = {
      type: "move",
      requestId: request.requestId,
      row,
      col,
      backend: "fallback",
      error: error instanceof Error ? error.message : String(error),
    };
  }

  self.postMessage(response);
};

export {};
