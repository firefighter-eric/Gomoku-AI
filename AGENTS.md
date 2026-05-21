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
uv run gomoku --mode human-ai --human black --depth 4
```

TUI 人机对战：

```bash
uv run gomoku --mode human-ai --human black --depth 4 --tui
```

GUI 人机对战：

```bash
uv run gomoku --mode human-ai --human black --depth 4 --ui gui
```

AI 对 AI：

```bash
uv run gomoku --mode ai-ai --black-depth 4 --white-depth 4 --delay 0.2
```

算法对比：

```bash
uv run gomoku-eval --first alpha-beta --first-version v2 --second alpha-beta --second-version v1 --first-depth 3 --second-depth 3 --games 8
```

正式算法评测以 `alpha-beta:v1` 为固定基线，每组对比 8 场，默认交替先后手。当前正式基线记录只跑 alpha-beta 家族版本，也就是 `alpha-beta:v2`、`alpha-beta:v3` 对 `alpha-beta:v1`；`random:v0` 只作为冒烟测试或历史最低参照，不再参与每轮正式基线赛。

`gomoku-eval` 默认 `--jobs 0`，即每局比赛一个独立进程；长深度评测优先使用这个默认并行方式。如果需要调试单局或排查非确定性问题，再显式设置 `--jobs 1`。

对比第一版和第二版：

```bash
uv run gomoku-eval --first alpha-beta --first-version v2 --second alpha-beta --second-version v1 --first-depth 3 --second-depth 3 --games 8
```

对比第一版和第三版：

```bash
uv run gomoku-eval --first alpha-beta --first-version v3 --second alpha-beta --second-version v1 --first-depth 3 --second-depth 3 --games 8
```

## 代码结构约定

- `gomoku_ai/core.py`：只放棋盘、规则、落子、胜负检测、坐标解析和基础渲染。不要让它依赖 CLI、TUI、GUI 或 AI。
- `gomoku_ai/ai.py`：只放 AI 搜索、评分、候选点、缓存相关逻辑。AI 应通过 `Board` 接口读写局面。当前 `v1` 是第一版历史复刻，`v2` 保留为第二版默认算法，`v3` 是全面检查后的第三版。
- `gomoku_ai/players.py`：放 AI 玩家协议、算法配置、算法注册和玩家工厂。新增算法应在这里注册，并实现 `choose_move(board)`。
- `gomoku_ai/evaluate.py`：放 AI 对 AI 批量评测逻辑和 `gomoku-eval` 命令入口，不要把评测循环塞进界面层。
- `gomoku_ai/game.py`：CLI、TUI、GUI 共用的对局会话、设置、回合结果和结算结果。
- `gomoku_ai/cli.py`：普通文本命令行入口和文本输入输出，不重新实现对局规则。
- `gomoku_ai/tui.py`：`curses` 终端界面、方向键/鼠标交互、结算菜单。
- `gomoku_ai/gui.py`：Pygame 图形界面、棋盘绘制、鼠标点击和 GUI 结算操作。
- `docs/algorithm-versions.md`：不同算法版本的详细说明、对比命令和新增版本约定。
- `docs/evaluation-results.md`：算法对局评测结果记录。正式强弱记录以 `v1` 为基线，每组 8 场。
- `tests/`：每个模块对应测试文件，新增行为必须补测试。

## 产品与规则约定

- 默认棋盘大小是 `15x15`。
- 默认胜利条件是五连或更长连线。
- 默认规则是自由规则五子棋。
- 默认 AI 搜索深度是 `4`。
- 默认注册名是 `alpha-beta`，默认版本是 `v2`。
- `random:v0` 是随机基线，`alpha-beta:v1` 是第一版，`alpha-beta:v2` 是第二版，`alpha-beta:v3` 是第三版。
- 注册名不要使用 `v0`、`v1` 这样的版本号；版本号通过 `version` 字段或 CLI 的 `--*-version` 参数表达。
- 正式算法强弱记录以 `alpha-beta:v1` 为基线，每组对比 8 场；当前每轮只跑 `v2`、`v3` 与它比赛并记录结果，不再跑 `v0`。
- 黑棋先手。
- 第一版不实现禁手、三三、四四、长连禁手等正式连珠规则。
- TUI 和 GUI 结束后必须停留在结算界面，允许用户调整难度、切换黑白、重新开始或退出；不要恢复成“按任意键退出”或自动关闭的行为。
- GUI 结算界面还需要允许通过下拉框切换算法版本。人机模式切换当前 AI 算法，AI 对 AI 模式分别切换黑白双方算法；`random:v0` 不使用搜索深度，界面上应禁用对应深度调整。

## 文档约定

- README 必须保持中文。
- 算法版本说明必须同步维护 `docs/algorithm-versions.md`。
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

涉及算法抽象或评测时，还需要确认：

- `uv run gomoku-eval --first alpha-beta --first-version v2 --second alpha-beta --second-version v1 --first-depth 1 --second-depth 1 --games 2 --size 5 --max-moves 2` 能输出对比结果。
- `uv run gomoku-eval --first random --first-version v0 --second random --second-version v0 --games 2 --size 5 --max-moves 1 --jobs 2` 能并行输出对比结果。
- 新算法必须通过统一玩家接口进入 `GameSession`，不要在 CLI、TUI 或 GUI 中按算法类型分支重写对局推进。
- 新算法需要有工厂注册、至少一个行为测试，以及必要时的对局评测测试。
- 算法版本升级要同步 README 的版本演进说明，并补棋型、候选裁剪或评测相关测试。

## 维护原则

- 保持核心逻辑与界面分离，避免把规则或对局推进重复写进 CLI/TUI/GUI。
- 保持算法实现与评测框架分离；新增算法应通过 `players.py` 暴露，评测应复用统一玩家接口。
- 保留可比较的旧算法版本，除非用户明确要求替换；面向棋力改进时优先新增版本，便于 `gomoku-eval` 做 A/B 对战。
- 保持 AI 参数可控，默认不要让一手棋等待过久。
- AI 性能很依赖候选点排序与候选宽度。不要把 `_move_order_score` 改回全盘评分，也不要在必胜判断中复制棋盘；高深度搜索应保留深层候选收窄策略。
- 优先补行为级测试，而不是只测试实现细节。
- 不要提交 `.venv/`、缓存、构建产物或系统临时文件。
- 如果新增依赖，说明为什么必须新增，并更新 `pyproject.toml` 与 README。
