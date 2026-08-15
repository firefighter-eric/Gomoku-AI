declare module "*gomoku_ai_wasm.js" {
  export default function init(): Promise<unknown>;
  export function choose_move_v5(
    grid: Int8Array,
    size: number,
    winLength: number,
    stone: number,
    depth: number,
    candidateRadius: number,
    candidateLimit: number,
    seed: bigint,
  ): Uint32Array;
}
