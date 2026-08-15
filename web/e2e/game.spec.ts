import { expect, test } from "@playwright/test";

test("human can play and the local AI replies", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("grid", { name: /十五路五子棋棋盘/ })).toBeVisible();
  await expect(page.getByRole("heading", { name: "你的回合" }).first()).toBeVisible();

  const board = page.getByRole("grid", { name: /十五路五子棋棋盘/ });
  const box = await board.boundingBox();
  if (!box) {
    throw new Error("board has no bounding box");
  }
  await page.mouse.click(box.x + box.width / 2, box.y + box.height / 2);

  await expect(page.locator(".game-status").filter({ visible: true }).getByText(/第 3 手/)).toBeVisible({ timeout: 20_000 });
  await expect(page.getByText("Rust · WebAssembly", { exact: true })).toBeVisible();
});

test("mobile layout remains inside the viewport", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== "mobile", "mobile-only assertion");
  await page.goto("/");
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  expect(overflow).toBeLessThanOrEqual(1);
  await expect(page.getByRole("button", { name: "重新开始" }).first()).toBeVisible();
  await expect(page.locator(".engine-note")).toContainText("所有计算均在浏览器本地完成");
});

test("desktop labels remain fully visible at a compact window size", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== "chromium", "desktop-only assertion");
  await page.setViewportSize({ width: 1280, height: 720 });
  await page.goto("/");

  expect(await page.title()).toBe("Gomoku-AI · 五子棋");
  await expect(page.getByText("浏览器版")).toHaveCount(0);

  const layout = await page.evaluate(() => {
    const controls = document.querySelector<HTMLElement>(".controls");
    const labels = Array.from(document.querySelectorAll<HTMLElement>(".control-label"));
    if (!controls) {
      throw new Error("controls panel is missing");
    }
    const controlsBox = controls.getBoundingClientRect();
    return {
      pageOverflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
      labelsInsidePanel: labels.every((label) => label.getBoundingClientRect().left >= controlsBox.left - 1),
      controlsOverflow: getComputedStyle(controls).overflow,
    };
  });

  expect(layout.pageOverflow).toBeLessThanOrEqual(1);
  expect(layout.labelsInsidePanel).toBe(true);
  expect(layout.controlsOverflow).toBe("visible");
});

test("two local players can alternate turns", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "双人对战" }).click();
  await expect(page.getByRole("heading", { name: "黑棋回合" }).first()).toBeVisible();

  const board = page.getByRole("grid", { name: /十五路五子棋棋盘/ });
  const box = await board.boundingBox();
  if (!box) {
    throw new Error("board has no bounding box");
  }
  await page.mouse.click(box.x + box.width / 2, box.y + box.height / 2);
  await expect(page.getByRole("heading", { name: "白棋回合" }).first()).toBeVisible();
});
