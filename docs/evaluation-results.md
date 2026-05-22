# 算法评测结果

本文档记录 `Gomoku-AI` 的正式算法对局结果。当前正式强弱记录使用 `alpha-beta:v1` 作为固定基线，每组对比 8 场，默认交替先后手，完整终局，不使用 `--max-moves` 截断。

`gomoku-eval` 默认 `--jobs 0`，表示每局比赛使用一个独立进程并行运行；如果某次记录使用了 `--jobs 1` 或其他进程数，需要在运行环境中注明。

当前每轮正式基线赛只跑 alpha-beta 家族版本，也就是 `alpha-beta:v2`、`alpha-beta:v3` 对 `alpha-beta:v1`。`random:v0` 只保留为冒烟测试或历史最低参照，不再参与每轮正式基线赛。

## 2026-05-22 基线评测

运行环境：

- 棋盘：默认 `15x15`
- 规则：自由规则五子棋
- 对局数：每组 8 场
- 先后手：默认交替
- 截断：无
- 搜索深度：`alpha-beta` 版本统一使用 depth 3；`random:v0` 不使用搜索深度

汇总：

| 对比组 | 待测版本胜局 | `alpha-beta:v1` 胜局 | 平局 | 停止 | 平均手数 | 结论 |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `random:v0` vs `alpha-beta:v1(d3)` | 0 | 8 | 0 | 0 | 10.0 | `v1` 稳定强于随机基线。 |
| `alpha-beta:v2(d3)` vs `alpha-beta:v1(d3)` | 4 | 4 | 0 | 0 | 26.0 | depth 3 下胜负持平，`v2` 主要体现速度优化。 |
| `alpha-beta:v3(d3)` vs `alpha-beta:v1(d3)` | 4 | 4 | 0 | 0 | 19.0 | depth 3 下胜负持平，平均手数短于 `v2` 对 `v1`。 |

### `random:v0` vs `alpha-beta:v1`

命令：

```bash
uv run gomoku-eval --first random --first-version v0 --second alpha-beta --second-version v1 --second-depth 3 --games 8
```

结果：

```text
Comparison: random:v0 vs alpha-beta:v1(d3)
Games: 8
random:v0 wins: 0
alpha-beta:v1(d3) wins: 8
Draws: 0
Stopped: 0
Average moves: 10.0
```

明细：

| 局 | 黑棋 | 白棋 | 胜者 | 手数 |
| ---: | --- | --- | --- | ---: |
| 1 | `random:v0` | `alpha-beta:v1(d3)` | `alpha-beta:v1(d3)` 执白 | 10 |
| 2 | `alpha-beta:v1(d3)` | `random:v0` | `alpha-beta:v1(d3)` 执黑 | 9 |
| 3 | `random:v0` | `alpha-beta:v1(d3)` | `alpha-beta:v1(d3)` 执白 | 10 |
| 4 | `alpha-beta:v1(d3)` | `random:v0` | `alpha-beta:v1(d3)` 执黑 | 9 |
| 5 | `random:v0` | `alpha-beta:v1(d3)` | `alpha-beta:v1(d3)` 执白 | 14 |
| 6 | `alpha-beta:v1(d3)` | `random:v0` | `alpha-beta:v1(d3)` 执黑 | 9 |
| 7 | `random:v0` | `alpha-beta:v1(d3)` | `alpha-beta:v1(d3)` 执白 | 10 |
| 8 | `alpha-beta:v1(d3)` | `random:v0` | `alpha-beta:v1(d3)` 执黑 | 9 |

### `alpha-beta:v2` vs `alpha-beta:v1`

命令：

```bash
uv run gomoku-eval --first alpha-beta --first-version v2 --second alpha-beta --second-version v1 --first-depth 3 --second-depth 3 --games 8
```

结果：

```text
Comparison: alpha-beta:v2(d3) vs alpha-beta:v1(d3)
Games: 8
alpha-beta:v2(d3) wins: 4
alpha-beta:v1(d3) wins: 4
Draws: 0
Stopped: 0
Average moves: 26.0
```

明细：

| 局 | 黑棋 | 白棋 | 胜者 | 手数 |
| ---: | --- | --- | --- | ---: |
| 1 | `alpha-beta:v2(d3)` | `alpha-beta:v1(d3)` | `alpha-beta:v1(d3)` 执白 | 40 |
| 2 | `alpha-beta:v1(d3)` | `alpha-beta:v2(d3)` | `alpha-beta:v2(d3)` 执白 | 12 |
| 3 | `alpha-beta:v2(d3)` | `alpha-beta:v1(d3)` | `alpha-beta:v1(d3)` 执白 | 40 |
| 4 | `alpha-beta:v1(d3)` | `alpha-beta:v2(d3)` | `alpha-beta:v2(d3)` 执白 | 12 |
| 5 | `alpha-beta:v2(d3)` | `alpha-beta:v1(d3)` | `alpha-beta:v1(d3)` 执白 | 40 |
| 6 | `alpha-beta:v1(d3)` | `alpha-beta:v2(d3)` | `alpha-beta:v2(d3)` 执白 | 12 |
| 7 | `alpha-beta:v2(d3)` | `alpha-beta:v1(d3)` | `alpha-beta:v1(d3)` 执白 | 40 |
| 8 | `alpha-beta:v1(d3)` | `alpha-beta:v2(d3)` | `alpha-beta:v2(d3)` 执白 | 12 |

### `alpha-beta:v3` vs `alpha-beta:v1`

命令：

```bash
uv run gomoku-eval --first alpha-beta --first-version v3 --second alpha-beta --second-version v1 --first-depth 3 --second-depth 3 --games 8
```

结果：

```text
Comparison: alpha-beta:v3(d3) vs alpha-beta:v1(d3)
Games: 8
alpha-beta:v3(d3) wins: 4
alpha-beta:v1(d3) wins: 4
Draws: 0
Stopped: 0
Average moves: 19.0
```

明细：

| 局 | 黑棋 | 白棋 | 胜者 | 手数 |
| ---: | --- | --- | --- | ---: |
| 1 | `alpha-beta:v3(d3)` | `alpha-beta:v1(d3)` | `alpha-beta:v1(d3)` 执白 | 12 |
| 2 | `alpha-beta:v1(d3)` | `alpha-beta:v3(d3)` | `alpha-beta:v3(d3)` 执白 | 26 |
| 3 | `alpha-beta:v3(d3)` | `alpha-beta:v1(d3)` | `alpha-beta:v1(d3)` 执白 | 12 |
| 4 | `alpha-beta:v1(d3)` | `alpha-beta:v3(d3)` | `alpha-beta:v3(d3)` 执白 | 26 |
| 5 | `alpha-beta:v3(d3)` | `alpha-beta:v1(d3)` | `alpha-beta:v1(d3)` 执白 | 12 |
| 6 | `alpha-beta:v1(d3)` | `alpha-beta:v3(d3)` | `alpha-beta:v3(d3)` 执白 | 26 |
| 7 | `alpha-beta:v3(d3)` | `alpha-beta:v1(d3)` | `alpha-beta:v1(d3)` 执白 | 12 |
| 8 | `alpha-beta:v1(d3)` | `alpha-beta:v3(d3)` | `alpha-beta:v3(d3)` 执白 | 26 |

## 2026-05-22 d=5 基线评测

运行环境：

- 棋盘：默认 `15x15`
- 规则：自由规则五子棋
- 对局数：每组 8 场
- 先后手：默认交替
- 截断：无
- 并行：默认 `--jobs 0`，每局一个独立进程
- 搜索深度：`alpha-beta` 版本统一使用 depth 5
- 范围：只记录 `alpha-beta:v2`、`alpha-beta:v3` 对 `alpha-beta:v1`；`random:v0` 不纳入本轮正式记录

注意：本节记录的是 `alpha-beta:v3` 增加双三、四三、双四显式加权之前的结果。该增强之后需要重新跑同深度基线赛，才能代表当前 `v3` 的水平。

汇总：

| 对比组 | 待测版本胜局 | `alpha-beta:v1` 胜局 | 平局 | 停止 | 平均手数 | 墙钟耗时 | 结论 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `alpha-beta:v2(d5)` vs `alpha-beta:v1(d5)` | 4 | 4 | 0 | 0 | 28.0 | 402.54s | depth 5 下胜负持平，8 局均为执黑方获胜。 |
| `alpha-beta:v3(d5)` vs `alpha-beta:v1(d5)` | 4 | 4 | 0 | 0 | 30.0 | 566.22s | depth 5 下胜负持平，平均手数和耗时均高于 `v2` 对 `v1`。 |

### `alpha-beta:v2` vs `alpha-beta:v1`

命令：

```bash
/usr/bin/time -p uv run gomoku-eval --first alpha-beta --first-version v2 --second alpha-beta --second-version v1 --first-depth 5 --second-depth 5 --games 8
```

结果：

```text
Comparison: alpha-beta:v2(d5) vs alpha-beta:v1(d5)
Games: 8
alpha-beta:v2(d5) wins: 4
alpha-beta:v1(d5) wins: 4
Draws: 0
Stopped: 0
Average moves: 28.0
real 402.54
user 3055.55
sys 27.36
```

明细：

| 局 | 黑棋 | 白棋 | 胜者 | 手数 |
| ---: | --- | --- | --- | ---: |
| 1 | `alpha-beta:v2(d5)` | `alpha-beta:v1(d5)` | `alpha-beta:v2(d5)` 执黑 | 31 |
| 2 | `alpha-beta:v1(d5)` | `alpha-beta:v2(d5)` | `alpha-beta:v1(d5)` 执黑 | 25 |
| 3 | `alpha-beta:v2(d5)` | `alpha-beta:v1(d5)` | `alpha-beta:v2(d5)` 执黑 | 31 |
| 4 | `alpha-beta:v1(d5)` | `alpha-beta:v2(d5)` | `alpha-beta:v1(d5)` 执黑 | 25 |
| 5 | `alpha-beta:v2(d5)` | `alpha-beta:v1(d5)` | `alpha-beta:v2(d5)` 执黑 | 31 |
| 6 | `alpha-beta:v1(d5)` | `alpha-beta:v2(d5)` | `alpha-beta:v1(d5)` 执黑 | 25 |
| 7 | `alpha-beta:v2(d5)` | `alpha-beta:v1(d5)` | `alpha-beta:v2(d5)` 执黑 | 31 |
| 8 | `alpha-beta:v1(d5)` | `alpha-beta:v2(d5)` | `alpha-beta:v1(d5)` 执黑 | 25 |

### `alpha-beta:v3` vs `alpha-beta:v1`

命令：

```bash
/usr/bin/time -p uv run gomoku-eval --first alpha-beta --first-version v3 --second alpha-beta --second-version v1 --first-depth 5 --second-depth 5 --games 8
```

结果：

```text
Comparison: alpha-beta:v3(d5) vs alpha-beta:v1(d5)
Games: 8
alpha-beta:v3(d5) wins: 4
alpha-beta:v1(d5) wins: 4
Draws: 0
Stopped: 0
Average moves: 30.0
real 566.22
user 4284.96
sys 48.00
```

明细：

| 局 | 黑棋 | 白棋 | 胜者 | 手数 |
| ---: | --- | --- | --- | ---: |
| 1 | `alpha-beta:v3(d5)` | `alpha-beta:v1(d5)` | `alpha-beta:v3(d5)` 执黑 | 27 |
| 2 | `alpha-beta:v1(d5)` | `alpha-beta:v3(d5)` | `alpha-beta:v1(d5)` 执黑 | 33 |
| 3 | `alpha-beta:v3(d5)` | `alpha-beta:v1(d5)` | `alpha-beta:v3(d5)` 执黑 | 27 |
| 4 | `alpha-beta:v1(d5)` | `alpha-beta:v3(d5)` | `alpha-beta:v1(d5)` 执黑 | 33 |
| 5 | `alpha-beta:v3(d5)` | `alpha-beta:v1(d5)` | `alpha-beta:v3(d5)` 执黑 | 27 |
| 6 | `alpha-beta:v1(d5)` | `alpha-beta:v3(d5)` | `alpha-beta:v1(d5)` 执黑 | 33 |
| 7 | `alpha-beta:v3(d5)` | `alpha-beta:v1(d5)` | `alpha-beta:v3(d5)` 执黑 | 27 |
| 8 | `alpha-beta:v1(d5)` | `alpha-beta:v3(d5)` | `alpha-beta:v1(d5)` 执黑 | 33 |

## 记录约定

- 正式版本对比优先使用 `alpha-beta:v1` 做基线。
- 每个 alpha-beta 待比较版本固定跑 8 场。
- `random:v0` 不再参与每轮正式基线赛；如需随机最低参照，需要在记录中单独标注。
- 默认交替先后手；如果使用 `--no-alternate-colors`，必须在记录中单独注明。
- 默认每局一个独立进程并行运行；如果使用非默认 `--jobs`，必须在记录中单独注明。
- 如果使用非默认棋盘大小、搜索深度或 `--max-moves`，必须在记录中单独注明，不要和正式基线结果混在一起。
- 结果表里的“待测版本胜局”指命令中的 `--first` 一方；如果待测版本放在 `--second`，记录时需要显式说明。
