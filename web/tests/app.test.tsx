import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";

import App from "../src/App";

describe("WebUI", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("renders the playable board and settings", () => {
    render(<App />);
    expect(screen.getByRole("link", { name: "Gomoku-AI 首页" })).toBeInTheDocument();
    expect(screen.getByRole("grid", { name: /十五路五子棋棋盘/ })).toBeInTheDocument();
    expect(screen.getAllByText("你的回合").length).toBeGreaterThan(0);
    expect(screen.getByRole("button", { name: "人机对战" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: "双人对战" })).toBeInTheDocument();
    expect(screen.getByRole("slider", { name: "AI 难度" })).toHaveValue("5");
    expect(screen.getAllByText("Alpha-Beta v5").length).toBeGreaterThan(0);
  });
});
