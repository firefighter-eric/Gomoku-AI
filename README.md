# Gomoku-AI

`Gomoku-AI` 是一个使用 Python 3.12 和 uv 构建的五子棋项目，支持人机对战、AI 对 AI 自动对战、可用方向键和鼠标操作的终端 TUI，以及 Pygame 图形界面。

项目参考 [firefighter-eric/TicTacToe-AI](https://github.com/firefighter-eric/TicTacToe-AI) 的算法思路：棋盘状态、胜负检测、启发式评分、Zobrist 缓存、邻域候选点生成、alpha-beta 搜索。当前实现没有照搬参考项目源码，而是拆成更清晰的核心逻辑、AI、共享对局会话和界面层，方便后续继续扩展。

## 功能

- 15x15 自由规则五子棋。
- 支持人机对战。
- 支持两个 AI 自动对战。
- 支持普通命令行坐标输入。
- 支持 TUI 模式：方向键选格、回车/空格落子、终端支持时可鼠标点击落子。
- 支持 Pygame GUI 模式：鼠标点击棋盘落子，右侧面板显示状态、难度、黑白和结算操作。
- 对局结束后在 TUI 结算界面中可以调整难度、切换黑白、重新开始或退出。
- 对局结束后在 GUI 结算界面中可以调整难度、切换黑白、重新开始或退出。
- AI 使用启发式评分、候选点裁剪、Zobrist 缓存和 alpha-beta 搜索。

## 环境

- Python `>=3.12`
- uv
- Pygame，由项目依赖自动安装。

本项目已经配置 `pyproject.toml`，常用命令都可以通过 `uv run ...` 执行。

## 启动游戏

进入项目目录：

```bash
cd /Users/eric/projects/Gomoku-AI
```

启动交互菜单：

```bash
uv run gomoku
```

## 人机对战

你执黑，先手：

```bash
uv run gomoku --mode human-ai --human black --depth 4
```

你执白，AI 先手：

```bash
uv run gomoku --mode human-ai --human white --depth 4
```

普通命令行模式下可以输入坐标，例如：

```text
H8
8 8
```

输入 `q`、`quit` 或 `exit` 可以退出。

## TUI 模式

启动 TUI 人机对战：

```bash
uv run gomoku --mode human-ai --human black --depth 4 --tui
```

也可以写成：

```bash
uv run gomoku --mode human-ai --human black --depth 4 --ui tui
```

TUI 对局中的操作：

- 方向键：移动选格。
- `H/J/K/L`：也可以移动选格。
- `Space` 或 `Enter`：落子。
- 鼠标点击：终端支持鼠标事件时，可以点击棋盘落子。
- `q`：退出当前对局。

TUI 结算界面中的操作：

- 上下键：选择菜单项。
- 左右键：调整难度（1 到 10）或切换黑白。
- `Enter`：确认菜单项。
- `Restart`：按当前结算界面中的设置重新开始。
- `Exit` 或 `q`：退出。

## GUI 模式

启动 GUI 人机对战：

```bash
uv run gomoku --mode human-ai --human black --depth 4 --ui gui
```

也可以写成：

```bash
uv run gomoku --mode human-ai --human black --depth 4 --gui
```

GUI 对局中的操作：

- 鼠标点击棋盘交叉点：落子。
- `Esc` 或 `q`：退出窗口。
- `Resign`：人机模式下认输。
- `Stop`：AI 对 AI 模式下停止当前对局。
- `Restart`：按当前设置重新开始。
- `Exit`：退出窗口。

GUI 结算界面会停留在最后局面。此时可以调整人机难度（1 到 10）、切换黑白，或调整 AI 对 AI 的黑白双方搜索深度（1 到 10），然后点击 `Restart` 开始新对局。

## AI 对 AI

启动两个 AI 自动对战：

```bash
uv run gomoku --mode ai-ai --black-depth 4 --white-depth 4 --delay 0.2
```

TUI 模式下观看 AI 对 AI：

```bash
uv run gomoku --mode ai-ai --black-depth 4 --white-depth 4 --delay 0.2 --tui
```

GUI 模式下观看 AI 对 AI：

```bash
uv run gomoku --mode ai-ai --black-depth 4 --white-depth 4 --delay 0.2 --ui gui
```

参数说明：

- `--black-depth`：黑棋 AI 搜索深度。
- `--white-depth`：白棋 AI 搜索深度。
- `--black-ai`：黑棋 AI 注册名，当前可选 `alpha-beta` 或 `random`。
- `--black-version`：黑棋 AI 版本，当前可选 `v0`、`v1`、`v2` 或 `v3`。
- `--white-ai`：白棋 AI 注册名，当前可选 `alpha-beta` 或 `random`。
- `--white-version`：白棋 AI 版本，当前可选 `v0`、`v1`、`v2` 或 `v3`。
- `--delay`：AI 每步之间的展示延迟，单位秒。

例如用 alpha-beta 对随机基线：

```bash
uv run gomoku --mode ai-ai --black-ai alpha-beta --black-version v2 --white-ai random --white-version v0 --black-depth 4 --delay 0.2
```

## 算法对比

项目把“会下棋的算法”抽象成统一的玩家接口。当前内置算法：

- `random:v0`：随机基线，主要用于测试和强弱对比。
- `alpha-beta:v1`：第一版 alpha-beta，保留“复制棋盘 + 全盘评分”的候选排序和模拟落子胜负判断，用作历史对照。
- `alpha-beta:v2`：第二版 alpha-beta，也是当前默认算法，实现局部候选排序、快速一步必胜/防守判断、深层候选收窄和 Zobrist 缓存。
- `alpha-beta:v3`：第三版 alpha-beta，在第二版基础上加强棋型评分，识别活四、冲四、跳四、活三等模式，并在候选裁剪时保留关键战术点。

运行批量对比：

```bash
uv run gomoku-eval --first alpha-beta --first-version v2 --second alpha-beta --second-version v1 --first-depth 3 --second-depth 3 --games 8
```

正式算法强弱记录以 `alpha-beta:v1` 为基线，每组对比固定 8 场，并默认交替先后手。当前正式记录只比较 alpha-beta 家族版本，也就是 `alpha-beta:v2`、`alpha-beta:v3` 分别对 `alpha-beta:v1`；`random:v0` 只作为冒烟测试或历史最低参照，不再参与每轮正式基线赛。

最新 d=5 基线结果：`alpha-beta:v2(d5)` 对 `alpha-beta:v1(d5)` 为 4:4，`alpha-beta:v3(d5)` 对 `alpha-beta:v1(d5)` 也是 4:4；完整明细和耗时见 [docs/evaluation-results.md](docs/evaluation-results.md)。

对比第一版和第二版：

```bash
uv run gomoku-eval --first alpha-beta --first-version v2 --second alpha-beta --second-version v1 --first-depth 3 --second-depth 3 --games 8
```

对比第一版和第三版：

```bash
uv run gomoku-eval --first alpha-beta --first-version v3 --second alpha-beta --second-version v1 --first-depth 3 --second-depth 3 --games 8
```

默认会交替先后手，输出双方胜局、平局、提前停止局数、平均手数和每局明细。评测结果记录在 [docs/evaluation-results.md](docs/evaluation-results.md)。新增算法时，只要实现 `choose_move(board)` 并在 `gomoku_ai/players.py` 中注册，就可以被 `GameSession`、AI 对 AI 和 `gomoku-eval` 复用。

`gomoku-eval` 默认 `--jobs 0`，表示每局比赛使用一个独立进程并行运行；需要排查问题或复现实验调度时，可以设置 `--jobs 1` 改回串行。

## 算法版本演进

详细说明见 [docs/algorithm-versions.md](docs/algorithm-versions.md)。

- `random:v0`：随机基线，不做搜索，只用于测试和胜率参照。
- `alpha-beta:v1`：第一版。参考 `firefighter-eric/TicTacToe-AI` 的思路，建立棋盘状态、胜负检测、启发式评分、Zobrist 缓存、邻域候选点生成和 alpha-beta 搜索的基础结构，并保留较慢的“复制棋盘 + 全盘评分”候选排序。
- `alpha-beta:v2`：第二版。将候选点排序从“复制棋盘 + 全盘评分”改为“落点附近四方向局部棋型评分”；一步必胜/防守判断改为直接方向计数；深层 alpha-beta 自动收窄候选分支。
- `alpha-beta:v3`：第三版。在 `v2` 基础上加强棋型识别和评估，避免活四、跳四、活三等关键形态被固定五格窗口低估；候选裁剪会保留必胜、防必胜和高价值战术候选，方便和 `v2` 做同深度对比。

## 规则

- 默认棋盘大小是 `15x15`。
- 默认采用自由规则五子棋。
- 默认 AI 搜索深度是 `4`。
- 黑棋先手。
- 横、竖、斜任意方向连续五个或五个以上同色棋子即胜。
- 第一版不实现禁手、三三禁手、四四禁手、长连禁手等正式连珠规则。

## 主要参数

```bash
uv run gomoku --help
```

常用参数：

- `--mode human-ai`：人机对战。
- `--mode ai-ai`：AI 对 AI。
- `--ui plain`：普通文本界面，默认值。
- `--ui tui` 或 `--tui`：方向键/鼠标 TUI。
- `--ui gui` 或 `--gui`：Pygame 图形界面。
- `--human black`：人类执黑。
- `--human white`：人类执白。
- `--ai alpha-beta`：人机对战中的 AI 注册名，默认值。
- `--ai-version v2`：人机对战中的 AI 版本，默认值。
- `--black-ai alpha-beta`：AI 对 AI 中黑棋注册名。
- `--black-version v2`：AI 对 AI 中黑棋版本。
- `--white-ai alpha-beta`：AI 对 AI 中白棋注册名。
- `--white-version v2`：AI 对 AI 中白棋版本。
- `--depth 4`：人机对战中的 AI 难度，默认值。
- `--size 15`：棋盘大小。
- `--max-moves N`：最多运行 N 手，主要用于测试或快速演示。

## 难度与速度

`--depth` 越大，AI 会看得越深，但耗时也会增加。当前实现做了几项加速：

- 候选点只从已有棋子周围生成。
- 落子排序使用局部棋型评分，避免每个候选点都全盘扫描。
- 一步必胜和一步防守使用快速方向计数，不复制棋盘。
- 深层搜索会自动缩窄候选分支，减少高深度下的爆炸。
- Zobrist 缓存会复用重复局面评分。

建议：

- 默认使用 `--depth 4`。
- 想要更快响应时可以使用 `--depth 2` 或 `--depth 3`。
- TUI 和 GUI 的结算界面可以在 1 到 10 之间调整难度。
- `--depth 6` 以上仍可能明显变慢，尤其是棋盘中后期候选点较多时。

## 项目结构

```text
gomoku_ai/
  core.py   # 棋盘、规则、落子、胜负检测、坐标解析和文本渲染
  ai.py     # 启发式评分、候选点生成、Zobrist 缓存、v1/v2/v3 alpha-beta 搜索
  players.py # AI 玩家协议、算法注册、工厂和随机基线
  evaluate.py # AI 算法对战评测和 gomoku-eval 入口
  game.py   # CLI、TUI、GUI 共用的对局会话、设置、回合结果和结算结果
  cli.py    # 普通命令行入口和文本输入输出
  tui.py    # 方向键/鼠标终端界面和结算菜单
  gui.py    # Pygame 图形界面、棋盘绘制、鼠标点击和 GUI 结算操作
tests/
  test_core.py
  test_ai.py
  test_game.py
  test_cli.py
  test_tui.py
  test_gui.py
docs/
  algorithm-versions.md # 不同算法版本的详细说明和对比命令
```

核心设计原则：

- `core.py` 不依赖 CLI、TUI 或 GUI。
- AI 只通过 `Board` 接口读写局面。
- 新算法应通过 `players.py` 注册，保持 `choose_move(board)` 这一统一接口。
- CLI、TUI 和 GUI 共用 `GameSession` 管理回合、AI 落子、认输、停止、重开和结算。
- 各界面只负责交互和渲染，不重新实现规则或 AI 对局推进。

## 测试

运行全部测试：

```bash
uv run pytest
```

当前测试覆盖：

- 横、竖、两条斜线五连胜。
- 超过五连也判胜。
- 越界、重复落子和非法棋子。
- 平局检测。
- 坐标解析。
- AI 首手下天元。
- AI 能发现一步必胜。
- AI 能阻挡对方一步必胜。
- 第三版 AI 能识别更高价值的活四、活三棋型，并在候选裁剪时保留关键战术点。
- AI 玩家工厂、随机基线和算法对比统计。
- 普通 CLI 对局循环。
- TUI 坐标映射、结算菜单、难度和黑白切换。
- GUI 坐标映射、按钮命中、结算设置动作。
- 共享 `GameSession` 的落子、非法落子、胜负、认输、重开和 `max_moves` 停止。

## 后续可扩展方向

- 增加更完整的五子棋棋型评分。
- 增加迭代加深和时间限制。
- 增加更多算法实现，并用 `gomoku-eval` 做批量胜率对比。
- 增加棋谱保存、复盘和悔棋。
- 增加正式连珠禁手规则。
