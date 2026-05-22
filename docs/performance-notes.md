# 性能优化记录

本文档记录 `Gomoku-AI` 的 AI 性能优化、验证方式和后续加速方向。正式棋力对局结果仍记录在 [evaluation-results.md](evaluation-results.md)。

## 2026-05-22 v4 候选点评分复用

背景：

- `alpha-beta:v3` 增加双三、四三、双四显式加权后，候选点评分需要同时计算棋型分和复合威胁；本轮把这些性能优化固化为 `alpha-beta:v4`。
- 初版实现中，同一个候选点在排序和战术保留阶段会重复扫描同一条线。
- `cProfile` 显示主要耗时集中在 `_ordered_candidates`、`_move_order_score`、`_score_line_v3`、`_v3_local_score_after_move` 和 `_evaluate_for_v3`。

改动：

- 新增 `V4LineAnalysis`、`V4MoveAnalysis`、`V4CandidateAnalysis`，把分数、威胁分类和战术保留标记打包。
- `AlphaBetaV4AI._ordered_candidates()` 对每个候选点只生成一次 `V4CandidateAnalysis`，排序和裁剪阶段复用同一结果。
- `_score_line_v4()` 统一走 `_analyze_line_v4()`，同一次线型分析同时返回评分和威胁分类。
- 基础窗口评分改为直接在 pattern 字符串上计算，避免在 v4 路径里对 list 反复切片和 `count()`。

Profile 局面：

```python
moves = [
    (7, 7, BLACK), (7, 8, WHITE), (8, 7, BLACK), (6, 7, WHITE),
    (8, 8, BLACK), (6, 8, WHITE), (7, 6, BLACK), (8, 6, WHITE),
    (6, 6, BLACK), (9, 7, WHITE), (5, 7, BLACK), (9, 8, WHITE),
]
ai = AlphaBetaV4AI(BLACK, depth=3, candidate_limit=14)
```

结果：

| 阶段 | 总耗时 | 函数调用数 | 节点数 | 选择落子 |
| --- | ---: | ---: | ---: | --- |
| 优化前 | 0.779s | 6,392,186 | 197 | `(9, 9)` |
| 复用候选分析后 | 0.593s | 4,212,548 | 197 | `(9, 9)` |
| 字符串窗口评分后 | 0.502s | 3,623,680 | 197 | `(9, 9)` |

本次优化没有改变该局面的搜索节点数和选择落子，主要收益来自减少重复评分与重复 pattern 扫描。在这个局面上，墙钟耗时下降约 35%。

固化为 `alpha-beta:v4` 后，在同一局面用当前代码做一次轻量验证：

| 版本 | 总耗时 | 节点数 | cache hits | 选择落子 |
| --- | ---: | ---: | ---: | --- |
| `alpha-beta:v3` | 0.246s | 197 | 12 | `(9, 9)` |
| `alpha-beta:v4` | 0.179s | 197 | 12 | `(9, 9)` |

这条记录只用于确认 `v4` 的实现边界和落点一致性，不替代正式 8 局棋力评测。

验证命令：

```bash
uv run pytest
uv run gomoku-eval --first alpha-beta --first-version v4 --second alpha-beta --second-version v1 --first-depth 1 --second-depth 1 --games 2 --size 5 --max-moves 2 --jobs 2
```

## 2026-05-23 v4 make/undo 与增量 Zobrist

背景：

- `alpha-beta:v4` 之前继承了基础 alpha-beta 搜索框架，递归里每个子节点都通过 `Board.with_move(...)` 复制整张棋盘。
- `_hash(board)` 每次计算 Zobrist key 时都会扫描当前棋盘石子，搜索节点越多，重复扫描越明显。
- 本轮按版本边界只优化 `v4`，`v1`、`v2`、`v3` 仍保留原有搜索框架，方便做历史版本对比。

改动：

- `Board` 新增 `make_move(...)` 和 `undo_move(...)`，落子时返回可恢复记录，撤子时恢复原格点和上一手 `last_move`。
- `ZobristHasher` 新增 `update_hash(...)`，通过单个落子的随机数异或完成增量更新。
- `AlphaBetaV4AI` 新增 v4 专用递归路径，搜索时原地落子、递归传递当前 hash，并在 `finally` 中撤子，保证调用 `choose_move(...)` 后外部棋盘状态不变。

验证：

- `tests/test_core.py` 覆盖 make/undo 恢复棋盘、恢复 `last_move` 和禁止非栈顶撤子。
- `tests/test_ai.py` 覆盖增量 Zobrist 与全盘 hash 一致，以及在 `Board.copy()` 被替换成抛错时 `alpha-beta:v4` 仍可完成搜索并保持原棋盘不变。

验证命令：

```bash
uv run pytest tests/test_core.py tests/test_ai.py
```

## 2026-05-23 v4 搜索状态继续增量化

背景：

- make/undo 和增量 Zobrist 解决了棋盘复制与 hash 扫描，但 `v4` 递归中仍有三类重复工作：置换表只缓存未剪枝结果，候选点每层从已有棋子邻域重建，叶子评估仍扫描全盘所有线。
- 本轮继续只优化 `alpha-beta:v4`，旧版本保留原框架，方便用 `gomoku-eval` 做 A/B 对比。

改动：

- `alpha-beta:v4` 改用标准置换表 entry，记录搜索深度、分数、`exact` / `lower` / `upper` bound 和当前节点最佳着法。
- 候选排序优先尝试置换表 best move，让 alpha-beta 更早收窄窗口并触发剪枝。
- 新增 v4 搜索状态：候选前沿在 make/undo 时按邻域计数增量更新，递归中直接从 frontier 取候选点。
- 新增 v4 增量评估器：维护双方总棋型分和中心偏置，落子时只重算穿过落点的横、竖、两条斜线，撤子时恢复旧分数。

验证：

- `tests/test_ai.py` 覆盖增量 frontier 与全量候选生成一致、增量评估与全量 v4 评分一致、置换表记录 bound 与最佳着法、最佳着法排序优先，以及 v4 搜索不依赖 `Board.copy()`。
- 在前一节相同中盘局面上轻量计时，`alpha-beta:v4(d3, candidate_limit=14)` 选择 `(9, 9)`，耗时约 `0.121s`，节点数 `197`，置换表 entry 数 `41`。

验证命令：

```bash
uv run pytest tests/test_ai.py
uv run pytest
uv run gomoku-eval --first alpha-beta --first-version v4 --second alpha-beta --second-version v1 --first-depth 1 --second-depth 1 --games 2 --size 5 --max-moves 2 --jobs 2
```

## 后续加速方向

仍然值得继续优化的热路径：

- 置换表目前没有容量上限、替换策略或命中率细分统计；长局可继续做缓存治理。
- 仍没有迭代加深和时间预算；GUI/TUI 高难度响应可以继续改进。
- 还没有开局库、常见定式或 VCF/连续冲四等专门战术搜索。
