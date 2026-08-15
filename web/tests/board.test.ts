import { describe, expect, it } from "vitest";

import { pointToCell } from "../src/game/geometry";

describe("board geometry", () => {
  it("maps the center and corners to intersections", () => {
    expect(pointToCell(380, 380)).toEqual({ row: 7, col: 7 });
    expect(pointToCell(54, 54)).toEqual({ row: 0, col: 0 });
    expect(pointToCell(706, 706)).toEqual({ row: 14, col: 14 });
  });

  it("rejects points outside the playable grid", () => {
    expect(pointToCell(10, 10)).toBeNull();
  });
});
