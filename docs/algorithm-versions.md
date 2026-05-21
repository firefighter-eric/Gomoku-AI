# 算法版本说明

本文档记录 `Gomoku-AI` 中不同算法版本的目标、实现边界、注册名、适用场景和对比方式。README 只保留简要介绍，算法细节和后续版本演进以本文档为准。

## 版本总览

| 注册名 | 版本 | 状态 | 定位 |
| --- | --- | --- | --- |
| `random` | `v0` | 测试/基线 | 不做搜索，随机选择候选点，主要用于冒烟测试和胜率参照。 |
| `alpha-beta` | `v1` | 历史复刻版 | 参考 `firefighter-eric/TicTacToe-AI` 思路搭建五子棋 AI 基础结构，用于和后续版本做性能/棋力对比。 |
| `alpha-beta` | `v2` | 当前默认 | 在第一版基础上做速度优化，适合作为稳定对照组。 |
| `alpha-beta` | `v3` | 当前增强版 | 在第二版基础上加强棋型评分和关键候选保留，用于棋力改进对比。 |

当前默认注册名是 `alpha-beta`，默认版本是 `v2`。注册名描述算法家族，版本号描述同一算法家族内的迭代；不要把 `v0`、`v1` 这样的版本号当成注册名。旧名称 `alphabeta-v1`、`alphabeta`、`alphabeta-v3` 仍作为兼容别名保留，但文档和命令示例统一使用“注册名 + 版本号”。

## 第一版：基础 alpha-beta

注册名：`alpha-beta`

版本：`v1`

第一版来自项目初始实现阶段，算法设计参考 [`firefighter-eric/TicTacToe-AI`](https://github.com/firefighter-eric/TicTacToe-AI) 的思路，但没有照搬其源码风格，而是按本项目的模块边界重新实现。当前代码中保留的是第一版行为的历史复刻版本，用于和后续版本比较。

核心机制：

- 使用 `Board` 管理棋盘状态、落子、胜负检测和坐标。
- 使用邻域候选点生成，避免每层都遍历全棋盘空点。
- 使用启发式评分评估局面。
- 使用 alpha-beta 搜索选择落子。
- 使用 Zobrist hash 缓存局面评分。

主要不足：

- 候选点排序依赖“复制棋盘 + 全盘评分”，候选多时开销很大。
- 一步必胜和一步防守判断通过模拟落子完成，会产生额外棋盘复制。
- 深层搜索使用固定候选宽度，不按深度自动收窄，深度上去以后分支爆炸明显。
- 棋型评分相对粗糙，容易低估跳四、活三等非连续但高威胁形态。

示例命令：

```bash
uv run gomoku --mode human-ai --ai alpha-beta --ai-version v1 --depth 3
uv run gomoku --mode ai-ai --black-ai alpha-beta --black-version v1 --white-ai alpha-beta --white-version v2 --black-depth 3 --white-depth 3
```

## 第二版：速度优化版 alpha-beta

注册名：`alpha-beta`

版本：`v2`

第二版是当前默认算法。它保留第一版的整体搜索架构，但把几个主要热路径换成更轻的实现。

核心改进：

- 候选点排序从“复制棋盘 + 全盘评分”改成“落点附近四方向局部棋型评分”。
- 一步必胜和一步防守判断不再复制棋盘，而是直接做方向计数。
- 深层 alpha-beta 会自动收窄候选分支，减少高深度分支爆炸。
- 保留 Zobrist 缓存、邻域候选点生成和启发式评估。

适用场景：

- 默认人机对战。
- AI 对 AI 的稳定参照组。
- 后续算法版本的基线对照。

已知边界：

- 棋型评分仍以固定窗口和局部连续计数为主，棋力上限有限。
- 搜索过程中仍使用 `Board.with_move(...)` 复制棋盘，深度很高时仍有性能天花板。
- 没有迭代加深、时间预算、开局库或标准置换表 bound。

示例命令：

```bash
uv run gomoku --mode human-ai --ai alpha-beta --ai-version v2 --depth 4
uv run gomoku --mode ai-ai --black-ai alpha-beta --black-version v2 --white-ai random --white-version v0 --black-depth 4
```

## 第三版：棋型增强版 alpha-beta

注册名：`alpha-beta`

版本：`v3`

第三版来自算法全面检查后的改进。它保留第二版作为 `v2`，新增 `v3` 用于并排比较。

核心改进：

- 新增更细的棋型模式评分，覆盖活四、冲四、跳四、活三、眠三、活二等形态。
- 局面评估使用第三版棋型评分，减少固定五格窗口对活四、跳四、活三的低估。
- 候选点裁剪时保留关键战术点，包括己方必胜、防对方必胜、活四相关候选和高价值进攻候选。
- 修复同一个 AI 实例跨不同棋盘大小复用时 Zobrist 表尺寸不匹配的问题。

适用场景：

- 和第二版 `v2` 做同深度棋力对比。
- 作为后续 V4 的直接基础。
- 测试更复杂棋型评分对实际胜率的影响。

已知边界：

- 第三版仍沿用第二版的 alpha-beta 主框架，没有引入 make/undo 增量搜索。
- 第三版仍是固定深度搜索，没有时间预算和迭代加深。
- 棋型模式是工程化启发式，并非完整职业连珠规则。
- 当前项目默认是自由规则五子棋，第三版不处理禁手、三三、四四或长连禁手。

示例命令：

```bash
uv run gomoku --mode human-ai --ai alpha-beta --ai-version v3 --depth 4
uv run gomoku --mode ai-ai --black-ai alpha-beta --black-version v3 --white-ai alpha-beta --white-version v2 --black-depth 4 --white-depth 4
```

## 随机基线

注册名：`random`

版本：`v0`

随机基线不做搜索，也不做棋型判断。它从邻域候选点中随机选择一个合法点，如果没有邻域候选点，则退回全盘合法点。

用途：

- 验证统一玩家接口是否正常。
- 给 `gomoku-eval` 提供快速冒烟测试。
- 作为最低强度基线，帮助确认新算法至少能稳定击败随机策略。

## 评测命令

查看主游戏支持的算法参数：

```bash
uv run gomoku --help
```

第一版对第二版：

```bash
uv run gomoku-eval --first alpha-beta --first-version v2 --second alpha-beta --second-version v1 --first-depth 3 --second-depth 3 --games 20
```

第二版对第三版：

```bash
uv run gomoku-eval --first alpha-beta --first-version v3 --second alpha-beta --second-version v2 --first-depth 4 --second-depth 4 --games 20
```

第一版对第三版：

```bash
uv run gomoku-eval --first alpha-beta --first-version v3 --second alpha-beta --second-version v1 --first-depth 3 --second-depth 3 --games 20
```

第三版对随机基线：

```bash
uv run gomoku-eval --first alpha-beta --first-version v3 --second random --second-version v0 --first-depth 4 --games 20
```

快速冒烟测试：

```bash
uv run gomoku-eval --first alpha-beta --first-version v3 --second alpha-beta --second-version v2 --first-depth 1 --second-depth 1 --games 2 --size 5 --max-moves 4
```

`gomoku-eval` 默认交替先后手，输出双方胜局、平局、提前停止局数、平均手数和每局明细。用 `--no-alternate-colors` 可以固定第一方执黑。

## 新增算法版本的约定

新增算法时遵循下面的路径：

1. 在合适模块中实现一个带 `choose_move(board)` 方法的玩家类。
2. 在 `gomoku_ai/players.py` 中注册算法家族名和版本号，并补充别名。
3. 在 `tests/test_players.py` 中覆盖工厂创建和标签显示。
4. 如果改变搜索、候选点、棋型评分或缓存，补充 `tests/test_ai.py` 中的行为测试。
5. 如果影响 CLI 参数或评测流程，补充 `tests/test_cli.py` 或 `tests/test_evaluate.py`。
6. 更新本文档和 README 中的算法摘要。

建议保留旧算法注册名，除非明确要删除。这样每一版都能通过 `gomoku-eval` 做稳定对比，而不是只能凭主观体感判断棋力变化。

## 后续候选版本

可以考虑的第四版方向：

- 使用 make/undo 落子和增量 Zobrist，减少搜索中的棋盘复制。
- 引入迭代加深和时间预算，让 GUI/TUI 高难度仍能保持响应。
- 使用标准置换表 entry，记录 exact、lower bound、upper bound 和最佳着法。
- 增加开局库或常见定式。
- 增加更系统的战术搜索，例如连续冲四、双三、双四和 VCF/VC2 类型强制胜检测。
