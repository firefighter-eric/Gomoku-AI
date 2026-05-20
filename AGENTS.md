# AGENTS.md

本文档给 Codex 或其他自动化工程助手使用。仓库文档面向中文读者，后续新增说明、注释性文档和 README 内容应优先使用中文。

## 项目目标

`Gomoku-AI` 是一个 Python 3.12 + uv 的五子棋项目，当前目标是提供稳定的核心棋盘规则、可玩的普通 CLI、人机 TUI、Pygame GUI、AI 对 AI 模式，以及后续继续扩展界面的清晰接口。

算法实现参考 `firefighter-eric/TicTacToe-AI` 的设计思路：

- 棋盘状态管理。
- 胜负检测。
- 启发式棋型评分。
- Zobrist 缓存。
- 邻域候选点生成。
- alpha-beta 搜索。

不要直接照搬参考项目压缩成单行的源码风格。本仓库要求代码结构清晰、模块边界明确、测试覆盖关键行为。

## 技术栈

- Python `>=3.12`
- uv
- pytest
- 标准库 `curses` 用于 TUI
- Pygame 用于 GUI

除非确实需要，不要给核心游戏逻辑引入额外运行时依赖。

## 常用命令

运行测试：

```bash
uv run pytest
```

查看 CLI 参数：

```bash
uv run gomoku --help
```

普通人机对战：

```bash
uv run gomoku --mode human-ai --human black --depth 3
```

TUI 人机对战：

```bash
uv run gomoku --mode human-ai --human black --depth 3 --tui
```

GUI 人机对战：

```bash
uv run gomoku --mode human-ai --human black --depth 3 --ui gui
```

AI 对 AI：

```bash
uv run gomoku --mode ai-ai --black-depth 3 --white-depth 2 --delay 0.2
```

## 代码结构约定

- `gomoku_ai/core.py`：只放棋盘、规则、落子、胜负检测、坐标解析和基础渲染。不要让它依赖 CLI、TUI、GUI 或 AI。
- `gomoku_ai/ai.py`：只放 AI 搜索、评分、候选点、缓存相关逻辑。AI 应通过 `Board` 接口读写局面。
- `gomoku_ai/game.py`：CLI、TUI、GUI 共用的对局会话、设置、回合结果和结算结果。
- `gomoku_ai/cli.py`：普通文本命令行入口和文本输入输出，不重新实现对局规则。
- `gomoku_ai/tui.py`：`curses` 终端界面、方向键/鼠标交互、结算菜单。
- `gomoku_ai/gui.py`：Pygame 图形界面、棋盘绘制、鼠标点击和 GUI 结算操作。
- `tests/`：每个模块对应测试文件，新增行为必须补测试。

## 产品与规则约定

- 默认棋盘大小是 `15x15`。
- 默认胜利条件是五连或更长连线。
- 默认规则是自由规则五子棋。
- 黑棋先手。
- 第一版不实现禁手、三三、四四、长连禁手等正式连珠规则。
- TUI 和 GUI 结束后必须停留在结算界面，允许用户调整难度、切换黑白、重新开始或退出；不要恢复成“按任意键退出”或自动关闭的行为。

## 文档约定

- README 必须保持中文。
- 用户可见的新功能、启动命令、参数和交互方式需要同步到 README。
- 如果改变项目架构、规则边界、测试命令或维护约定，需要同步更新本文件。
- 不要只在聊天里解释重要行为，应该把稳定约定写进文档。

## 测试约定

改动后至少运行：

```bash
uv run pytest
```

涉及 TUI 时，还需要确认：

- `uv run gomoku --help` 能展示相关参数。
- TUI 结算菜单不会在最后一步自动退出。
- 方向键、回车、鼠标映射相关逻辑有单元测试覆盖。

涉及 GUI 时，还需要确认：

- `uv run gomoku --help` 能展示 `--ui gui` 和 `--gui`。
- GUI 坐标映射、按钮命中和结算设置动作有单元测试覆盖。
- GUI 对局结束后不会自动退出，仍停留在结算界面。

## 维护原则

- 保持核心逻辑与界面分离，避免把规则或对局推进重复写进 CLI/TUI/GUI。
- 保持 AI 参数可控，默认不要让一手棋等待过久。
- AI 性能很依赖候选点排序与候选宽度。不要把 `_move_order_score` 改回全盘评分，也不要在必胜判断中复制棋盘；高深度搜索应保留深层候选收窄策略。
- 优先补行为级测试，而不是只测试实现细节。
- 不要提交 `.venv/`、缓存、构建产物或系统临时文件。
- 如果新增依赖，说明为什么必须新增，并更新 `pyproject.toml` 与 README。
