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

## 2026-05-23 v5 Rust 搜索引擎

背景：

- `alpha-beta:v4` 已经把 Python 侧搜索状态尽量做成 make/undo、增量 hash、增量候选前沿和增量评估，但递归搜索、候选排序和棋型扫描仍会反复穿过 Python 解释器。
- 本轮新增 `alpha-beta:v5`，目标是保持 Python `Board`、CLI/TUI/GUI 和评测框架不变，把核心 alpha-beta 热路径迁入 Rust。
- 当前机器的 Rust toolchain 较旧，为避免把项目构建绑定到外部 crate 下载和 PyO3 编译，首版 v5 采用无外部 crate 的 Rust 二进制引擎 `gomoku-ai-rust-engine`，由 Python 包装层通过子进程调用。

改动：

- 新增 `Cargo.toml`、`src/lib.rs` 和 `src/main.rs`。Rust 内核负责候选生成、一步必胜/防守、候选排序、棋型评分、Zobrist、置换表和 alpha-beta 递归。
- 新增 `gomoku_ai/rust_backend.py`，负责查找 `target/release/gomoku-ai-rust-engine` 或 `target/debug/gomoku-ai-rust-engine`，传入棋盘快照并解析 `(row, col, nodes, cache_hits)`。
- 新增 `AlphaBetaV5AI`。Rust 引擎存在时使用 `rust-engine` 后端；缺失时回退到 `AlphaBetaV4AI`，保证所有入口仍可用。
- `players.py` 把默认 `alpha-beta` / `alphabeta` 解析到 `v5`，旧版本 `v1` 到 `v4` 保留为可比较版本。

构建命令：

```bash
cargo build --release
```

固定局面：

```python
moves = [
    (7, 7, BLACK), (7, 8, WHITE), (8, 7, BLACK), (6, 7, WHITE),
    (8, 8, BLACK), (6, 8, WHITE), (7, 6, BLACK), (8, 6, WHITE),
    (6, 6, BLACK), (9, 7, WHITE), (5, 7, BLACK), (9, 8, WHITE),
]
```

轻量计时结果，每个版本重复 5 次，表中为平均耗时；v5 结果包含 Python 启动 Rust 子进程、传输棋盘和解析输出的开销：

| 深度 | 版本 | 平均耗时 | 最快耗时 | 节点数 | cache hits | 选择落子 | 后端 |
| ---: | --- | ---: | ---: | ---: | ---: | --- | --- |
| 3 | `alpha-beta:v4` | 0.1174s | 0.1164s | 197 | 0 | `(9, 9)` | Python |
| 3 | `alpha-beta:v5` | 0.0193s | 0.0189s | 197 | 0 | `(9, 9)` | Rust engine |
| 4 | `alpha-beta:v4` | 0.5995s | 0.5931s | 421 | 23 | `(9, 9)` | Python |
| 4 | `alpha-beta:v5` | 0.0602s | 0.0599s | 421 | 23 | `(9, 9)` | Rust engine |

在该局面上，v5 与 v4 保持相同落子、节点数和置换表命中数，depth 3 墙钟约提升 `6.1x`，depth 4 墙钟约提升 `10.0x`。

验证命令：

```bash
cargo test
uv run pytest
uv run gomoku --help
uv run gomoku-eval --first alpha-beta --first-version v5 --second alpha-beta --second-version v1 --first-depth 1 --second-depth 1 --games 2 --size 5 --max-moves 2
uv run gomoku-eval --first random --first-version v0 --second random --second-version v0 --games 2 --size 5 --max-moves 1 --jobs 2
```

## 后续加速方向

仍然值得继续优化的热路径：

- 置换表目前没有容量上限、替换策略或命中率细分统计；长局可继续做缓存治理。
- 仍没有迭代加深和时间预算；GUI/TUI 高难度响应可以继续改进。
- 还没有开局库、常见定式或 VCF/连续冲四等专门战术搜索。
- v5 当前是一次 `choose_move(...)` 调用一个 Rust 子进程；如果后续低深度响应也要进一步优化，可以考虑 PyO3 扩展、常驻 Rust worker 或 root-level 并行。

### 加速库选型

除多进程或多线程并行外，还可以通过编译型加速库降低 Python 解释器开销。当前 `alpha-beta:v4` 的热路径主要是递归搜索、候选点评分、棋型扫描、胜负检测和 make/undo 状态维护；这些逻辑包含大量小循环、分支和整数操作，不是普通大矩阵计算，所以库的适配性比“名义速度”更重要。

优先级建议：

1. Numba：优先做小范围原型。Numba 适合 NumPy 数组、数值函数和循环，可以把函数 JIT 编译成机器码。若要在本项目中发挥作用，需要先把棋盘从嵌套 Python list 改成 `int8`/`int16` 一维或二维数组，并把评分、胜负检测、候选生成等热函数改成 `@njit(cache=True)` 能进入 nopython 模式的数值内核。它的优点是原型速度快；风险是当前 dataclass、Python 对象、字符串 pattern 扫描和字典置换表需要重构。参考：[Numba 5 minute guide](https://numba.readthedocs.io/en/stable/user/5minguide.html)。
2. Cython：适合把稳定的热函数迁到编译扩展里。Cython 可以给 Python 代码加静态类型并编译成 C 扩展，适合 `_score_line_v4`、候选点评分、胜负检测、局部评估和搜索内核这类递归/分支/小循环密集代码。它比 Numba 更工程化，维护成本略高，但对 alpha-beta 这种控制流复杂的代码通常更可控。参考：[Cython](https://cython.org/)。
3. mypyc：适合低侵入实验。mypyc 能把带类型标注的 Python 模块编译成 C 扩展，现有代码如果进一步补类型，可能用较小改动换取中等收益。风险是项目仍处于较早阶段，复杂动态特性、对象模型和调试边界需要单独验证。参考：[mypyc introduction](https://mypyc.readthedocs.io/en/latest/introduction.html)。
4. Rust：适合长期高性能版本。当前已经以无外部 crate 的 Rust 二进制引擎落地为 `alpha-beta:v5`，把棋盘表示、候选生成、评分、置换表和 alpha-beta 搜索核心迁成 Rust 原生逻辑，Python 只保留 CLI/TUI/GUI、统一玩家接口和 fallback。后续如果要减少子进程开销，可以再评估 PyO3/maturin 扩展。参考：[PyO3](https://docs.rs/pyo3/latest/pyo3/) 和 [maturin](https://www.maturin.rs/)。
5. PyPy：可作为纯 Python 对照实验，但不是当前首选。PyPy 的 JIT 对纯 Python 算法代码可能有收益，但需要验证 Python 版本、uv 项目环境、Pygame/C 扩展兼容性和实际搜索热路径表现。当前项目要求 Python `>=3.12`，因此不要把 PyPy 作为默认路线。

不优先的方向：

- 直接 NumPy 化整套搜索：NumPy 擅长大数组批量向量化，五子棋 alpha-beta 则是小棋盘、递归分支和频繁剪枝。可以用 NumPy 作为 Numba 内核的数据容器，但不宜指望简单替换 list 后自动大幅加速。
- GPU/JAX/CuPy：当前启发式 alpha-beta 不是大批量矩阵计算，GPU 调度和数据搬运开销大概率抵消收益。除非后续引入神经网络评估器、批量 MCTS 或一次性批量评估大量局面，否则不作为近期方向。

落地顺序建议：

1. 先用 `cProfile` 或 `pyinstrument` 锁定当前 d=4/d=5 热点，建立固定局面基准。
2. 做 Numba 原型，只迁一个最热且容易数值化的函数族，例如线型评分和胜负检测。
3. 如果 Numba 原型收益稳定，再考虑把棋盘表示抽象为可选数组后端。
4. 如果 Numba 改造过重或 nopython 难以稳定通过，转向 Cython 热函数模块。
5. 如果目标是进一步降低 v5 低深度调用开销，再规划 PyO3 扩展或常驻 Rust worker，并保持旧 Python 版本可对照评测。

### 单手棋并行搜索

当前并行能力只存在于评测层：`gomoku-eval --jobs 0` 会把每一局比赛放到独立进程中运行。实际对局中，`AlphaBetaV4AI.choose_move(board)` 仍在单进程内串行搜索所有顶层候选点。

minimax / alpha-beta 的并行化已有成熟研究路线，包括 Distributed Tree Search、Young Brothers Wait Concept、ABDADA、APHID 和 TDSAB。它们的共同问题是：并行搜索过早展开兄弟分支时，可能浪费本来会被 alpha-beta 边界剪掉的工作；如果要跨进程或跨机器共享置换表，还会引入通信、同步和重复搜索控制成本。

对当前 Python 实现，优先级最高的落地方案是 root-level parallel alpha-beta：

1. 主进程按现有逻辑生成、排序和裁剪顶层候选点。
2. 先串行搜索第一个候选点，尽快得到较好的初始 `alpha`。
3. 将剩余候选点按任务分发给多个 worker，每个 worker 使用独立 AI 实例搜索对应子树。
4. 主进程收集 `(score, move)`，按现有候选顺序做确定性 tie-break。
5. 首版不共享置换表，只把并行作为可选参数，例如后续可设计为 `search_jobs=1` 默认关闭。

这个方案实现成本低，适合验证深度 5 以上或中后盘候选点较多时的墙钟收益。它不会替代现有 `gomoku-eval --jobs`：前者加速单手棋搜索，后者加速多局评测批量运行。若 root-level 并行收益稳定，再考虑更复杂的 YBWC 式延迟并行、共享/分片置换表或异步搜索。
