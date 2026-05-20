# Gomoku-AI

`Gomoku-AI` 是一个使用 Python 3.12 和 uv 构建的五子棋项目，支持人机对战、AI 对 AI 自动对战，以及一个可用方向键和鼠标操作的终端 TUI。

项目参考 [firefighter-eric/TicTacToe-AI](https://github.com/firefighter-eric/TicTacToe-AI) 的算法思路：棋盘状态、胜负检测、启发式评分、Zobrist 缓存、邻域候选点生成、alpha-beta 搜索。当前实现没有照搬参考项目源码，而是拆成更清晰的核心逻辑、AI 和界面层，方便后续继续接图形界面。

## 功能

- 15x15 自由规则五子棋。
- 支持人机对战。
- 支持两个 AI 自动对战。
- 支持普通命令行坐标输入。
- 支持 TUI 模式：方向键选格、回车/空格落子、终端支持时可鼠标点击落子。
- 对局结束后在 TUI 结算界面中可以调整难度、切换黑白、重新开始或退出。
- AI 使用启发式评分、候选点裁剪、Zobrist 缓存和 alpha-beta 搜索。

## 环境

- Python `>=3.12`
- uv

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
uv run gomoku --mode human-ai --human black --depth 3
```

你执白，AI 先手：

```bash
uv run gomoku --mode human-ai --human white --depth 3
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
uv run gomoku --mode human-ai --human black --depth 3 --tui
```

也可以写成：

```bash
uv run gomoku --mode human-ai --human black --depth 3 --ui tui
```

TUI 对局中的操作：

- 方向键：移动选格。
- `H/J/K/L`：也可以移动选格。
- `Space` 或 `Enter`：落子。
- 鼠标点击：终端支持鼠标事件时，可以点击棋盘落子。
- `q`：退出当前对局。

TUI 结算界面中的操作：

- 上下键：选择菜单项。
- 左右键：调整难度或切换黑白。
- `Enter`：确认菜单项。
- `Restart`：按当前结算界面中的设置重新开始。
- `Exit` 或 `q`：退出。

## AI 对 AI

启动两个 AI 自动对战：

```bash
uv run gomoku --mode ai-ai --black-depth 3 --white-depth 2 --delay 0.2
```

TUI 模式下观看 AI 对 AI：

```bash
uv run gomoku --mode ai-ai --black-depth 3 --white-depth 2 --delay 0.2 --tui
```

参数说明：

- `--black-depth`：黑棋 AI 搜索深度。
- `--white-depth`：白棋 AI 搜索深度。
- `--delay`：AI 每步之间的展示延迟，单位秒。

## 规则

- 默认棋盘大小是 `15x15`。
- 默认采用自由规则五子棋。
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
- `--human black`：人类执黑。
- `--human white`：人类执白。
- `--depth 3`：人机对战中的 AI 难度。
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

- 日常游玩使用 `--depth 2` 或 `--depth 3`。
- 想要更强棋力时使用 `--depth 4`。
- `--depth 5` 以上仍可能明显变慢，尤其是棋盘中后期候选点较多时。

## 项目结构

```text
gomoku_ai/
  core.py   # 棋盘、规则、落子、胜负检测、坐标解析和文本渲染
  ai.py     # 启发式评分、候选点生成、Zobrist 缓存、alpha-beta 搜索
  cli.py    # 普通命令行入口、人机对战和 AI 对 AI 对局循环
  tui.py    # 方向键/鼠标终端界面和结算菜单
tests/
  test_core.py
  test_ai.py
  test_cli.py
  test_tui.py
```

核心设计原则：

- `core.py` 不依赖 CLI/TUI，方便未来接 GUI。
- AI 只通过 `Board` 接口读写局面。
- 普通 CLI 和 TUI 共用同一套棋盘与 AI 逻辑。
- TUI 只负责交互和渲染，不重新实现规则。

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
- 普通 CLI 对局循环。
- TUI 坐标映射、结算菜单、难度和黑白切换。

## 后续可扩展方向

- 增加 Pygame 或其他图形界面。
- 增加更完整的五子棋棋型评分。
- 增加迭代加深和时间限制。
- 增加棋谱保存、复盘和悔棋。
- 增加正式连珠禁手规则。
