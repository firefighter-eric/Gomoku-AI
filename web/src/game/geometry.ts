import { BOARD_SIZE } from "./rules";

export const VIEWBOX_SIZE = 760;
export const BOARD_PADDING = 54;
export const GRID_SIZE = VIEWBOX_SIZE - BOARD_PADDING * 2;

export function pointToCell(
  x: number,
  y: number,
  size = BOARD_SIZE,
): { row: number; col: number } | null {
  const step = GRID_SIZE / (size - 1);
  const col = Math.round((x - BOARD_PADDING) / step);
  const row = Math.round((y - BOARD_PADDING) / step);
  const tolerance = step * 0.48;
  const targetX = BOARD_PADDING + col * step;
  const targetY = BOARD_PADDING + row * step;
  if (
    row < 0 ||
    col < 0 ||
    row >= size ||
    col >= size ||
    Math.abs(x - targetX) > tolerance ||
    Math.abs(y - targetY) > tolerance
  ) {
    return null;
  }
  return { row, col };
}
