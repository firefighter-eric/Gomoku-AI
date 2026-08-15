import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it } from "vitest";

import App from "../src/App";

describe("WebUI", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("persists the sound preference", async () => {
    const user = userEvent.setup();
    const view = render(<App />);
    const soundToggle = screen.getByRole("button", { name: "关闭音效" });
    expect(soundToggle).toHaveAttribute("aria-pressed", "true");

    await user.click(soundToggle);
    expect(screen.getByRole("button", { name: "开启音效" })).toHaveAttribute("aria-pressed", "false");
    await waitFor(() => {
      const saved = JSON.parse(localStorage.getItem("gomoku-ai.web.settings.v1") ?? "null");
      expect(saved.soundEnabled).toBe(false);
    });

    view.unmount();
    render(<App />);
    expect(screen.getByRole("button", { name: "开启音效" })).toHaveAttribute("aria-pressed", "false");
  });

  it("renders the playable board and settings", () => {
    render(<App />);
    expect(screen.getByRole("link", { name: "Gomoku-AI 首页" })).toBeInTheDocument();
    expect(screen.getByText("五子棋", { exact: true })).toBeInTheDocument();
    expect(screen.queryByText(/浏览器版/)).not.toBeInTheDocument();
    expect(screen.getByRole("grid", { name: /十五路五子棋棋盘/ })).toBeInTheDocument();
    expect(screen.getAllByText("你的回合").length).toBeGreaterThan(0);
    expect(screen.getByRole("button", { name: "人机对战" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: "双人对战" })).toBeInTheDocument();
    expect(screen.getByRole("slider", { name: "AI 难度" })).toHaveValue("5");
    expect(screen.getAllByText("Alpha-Beta v5").length).toBeGreaterThan(0);
  });
});
