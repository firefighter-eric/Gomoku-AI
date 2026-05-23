# 算法版本说明

本文档记录 `Gomoku-AI` 中不同算法版本的目标、实现边界、注册名、适用场景和对比方式。README 只保留简要介绍，算法细节和后续版本演进以本文档为准。

性能优化记录见 [performance-notes.md](performance-notes.md)，正式对局结果见 [evaluation-results.md](evaluation-results.md)。

## 版本总览

| 注册名 | 版本 | 状态 | 定位 |
| --- | --- | --- | --- |
| `random` | `v0` | 测试/基线 | 不做搜索，随机选择候选点，主要用于冒烟测试和胜率参照。 |
| `alpha-beta` | `v1` | 历史复刻版 | 参考 `firefighter-eric/TicTacToe-AI` 思路搭建五子棋 AI 基础结构，用于和后续版本做性能/棋力对比。 |
| `alpha-beta` | `v2` | 速度优化版 | 在第一版基础上做速度优化，适合作为稳定对照组。 |
| `alpha-beta` | `v3` | 棋型增强版 | 在第二版基础上加强棋型评分和关键候选保留，用于棋力改进对比。 |
| `alpha-beta` | `v4` | 当前默认 | 在第三版基础上整合候选分析复用和字符串窗口评分，用于性能优化对比。 |

当前默认注册名是 `alpha-beta`，默认版本是 `v4`。注册名描述算法家族，版本号描述同一算法家族内的迭代；不要把 `v0`、`v1` 这样的版本号当成注册名。旧名称 `alphabeta-v1`、`alphabeta-v3`、`alphabeta-v4` 等仍作为兼容别名保留；无版本的 `alphabeta` / `alpha-beta` 会解析到当前默认版本。

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

第二版保留第一版的整体搜索架构，但把几个主要热路径换成更轻的实现。它曾作为默认算法保留，现在主要作为速度优化版和稳定对照组。

核心改进：

- 候选点排序从“复制棋盘 + 全盘评分”改成“落点附近四方向局部棋型评分”。
- 一步必胜和一步防守判断不再复制棋盘，而是直接做方向计数。
- 深层 alpha-beta 会自动收窄候选分支，减少高深度分支爆炸。
- 保留 Zobrist 缓存、邻域候选点生成和启发式评估。

适用场景：

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

第三版来自算法全面检查后的改进。它保留第二版作为 `v2`，新增 `v3` 用于并排比较；当前主要作为棋型增强基线，默认 AI 已切换到 `alpha-beta:v4`。

核心改进：

- 新增更细的棋型模式评分，覆盖活四、冲四、跳四、活三、眠三、活二等形态。
- 对落点级复合威胁增加显式加权：双四 `2,000,000`、四三 `1,200,000`、双三 `80,000`。
- 局面评估使用第三版棋型评分，减少固定五格窗口对活四、跳四、活三的低估。
- 候选点裁剪时保留关键战术点，包括己方必胜、防对方必胜、活四、双四、四三、己方双三和防对方双三候选。
- 修复同一个 AI 实例跨不同棋盘大小复用时 Zobrist 表尺寸不匹配的问题。

适用场景：

- 和第二版 `v2` 做同深度棋力对比。
- 作为第四版 `v4` 的直接基础。
- 测试更复杂棋型评分对实际胜率的影响。

已知边界：

- 第三版仍沿用第二版的 alpha-beta 主框架，没有引入 make/undo 增量搜索。
- 第三版仍是固定深度搜索，没有时间预算和迭代加深。
- 棋型模式是工程化启发式，并非完整职业连珠规则；双三在自由规则下作为高价值威胁处理，不作为禁手处理。
- 当前项目默认是自由规则五子棋，第三版不处理禁手、三三、四四或长连禁手。

示例命令：

```bash
uv run gomoku --mode human-ai --ai alpha-beta --ai-version v3 --depth 4
uv run gomoku --mode ai-ai --black-ai alpha-beta --black-version v3 --white-ai alpha-beta --white-version v2 --black-depth 4 --white-depth 4
```

## 第四版：性能复用版 alpha-beta

注册名：`alpha-beta`

版本：`v4`

第四版把上一轮性能检查中验证过的优化固化成新版本。它继承第三版的棋型评分、双四/四三/双三显式加权和战术候选保留，但把热路径里的重复分析合并，方便后续把 `v3` 和 `v4` 分开做性能/棋力对比。

核心改进：

- 候选点排序和战术保留阶段复用同一个 `V4CandidateAnalysis`，避免同一个候选点重复计算评分和威胁分类。
- 落点四方向分析通过 `V4MoveAnalysis` 同时返回总分和 `V3MoveThreats`，避免评分和威胁判断各扫一遍线。
- 线型分析通过 `V4LineAnalysis` 同时返回棋型分和威胁分类。
- 基础五格窗口评分改为直接在 pattern 字符串上计算，减少列表切片和 `count()` 的重复开销。
- 搜索递归只在 `v4` 路径中使用 `Board.make_move(...)` / `Board.undo_move(...)` 原地落子和撤子，不再为每个子节点复制棋盘。
- `v4` 搜索把当前 Zobrist hash 作为递归状态传递，每次落子用单点异或增量更新，避免每个搜索节点重新扫描棋盘石子计算 hash。
- `v4` 使用标准置换表 entry，记录 `exact`、`lower`、`upper` 三类 bound、搜索深度、分数和最佳着法。
- 候选排序会优先尝试置换表中的最佳着法，让 alpha-beta 更早拿到可剪枝的上下界。
- 搜索状态维护增量候选前沿，make/undo 时只更新新落子附近的候选空点，不再每层从全盘已有棋子重建候选集合。
- 叶子评估维护双方总棋型分和中心偏置，make/undo 时只重算穿过落点的横、竖、两条斜线，避免每个叶子扫描所有行、列和对角线。
- 默认 `alpha-beta` / `alphabeta` 别名解析到 `v4`。

适用场景：

- 当前默认人机对战、TUI、GUI 和 AI 对 AI 算法。
- 和 `v3` 做同棋型语义下的性能对比。
- 和 `v1` 做正式 8 局基线赛，记录第四版综合表现。

已知边界：

- make/undo、增量 Zobrist、标准置换表、增量候选前沿和增量局部评估目前只用于 `alpha-beta:v4` 的搜索递归，`v1`、`v2`、`v3` 保持原有复制棋盘搜索框架，方便继续做版本对比。
- 仍没有迭代加深和时间预算，也没有开局库或专门的 VCF/连续冲四战术搜索。

示例命令：

```bash
uv run gomoku --mode human-ai --ai alpha-beta --ai-version v4 --depth 4
uv run gomoku --mode ai-ai --black-ai alpha-beta --black-version v4 --white-ai alpha-beta --white-version v3 --black-depth 4 --white-depth 4
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

正式算法强弱记录使用固定规约：`alpha-beta:v1` 作为基线，每个待比较版本与它比赛 8 场，默认交替先后手。当前正式记录只比较 alpha-beta 家族版本，也就是 `alpha-beta:v2`、`alpha-beta:v3`、`alpha-beta:v4` 分别对 `alpha-beta:v1`；结果写入 [evaluation-results.md](evaluation-results.md)。`random:v0` 只作为冒烟测试或历史最低参照，不再参与每轮正式基线赛。

当前 d=5 基线结果：`alpha-beta:v2(d5)`、`alpha-beta:v3(d5)`、`alpha-beta:v4(d5)` 对 `alpha-beta:v1(d5)` 都是 4:4；其中 `v4(d5)` 墙钟耗时为 443.05s，完整逐局明细和墙钟耗时见 [evaluation-results.md](evaluation-results.md)。

第二版对第一版：

```bash
uv run gomoku-eval --first alpha-beta --first-version v2 --second alpha-beta --second-version v1 --first-depth 3 --second-depth 3 --games 8
```

第三版对第一版：

```bash
uv run gomoku-eval --first alpha-beta --first-version v3 --second alpha-beta --second-version v1 --first-depth 3 --second-depth 3 --games 8
```

第四版对第一版：

```bash
uv run gomoku-eval --first alpha-beta --first-version v4 --second alpha-beta --second-version v1 --first-depth 3 --second-depth 3 --games 8
```

第四版对第三版属于探索性横向对比，不替代基线记录：

```bash
uv run gomoku-eval --first alpha-beta --first-version v4 --second alpha-beta --second-version v3 --first-depth 4 --second-depth 4 --games 8
```

快速冒烟测试：

```bash
uv run gomoku-eval --first alpha-beta --first-version v4 --second alpha-beta --second-version v3 --first-depth 1 --second-depth 1 --games 2 --size 5 --max-moves 4
```

`gomoku-eval` 默认交替先后手，默认场数为 8，默认 `--jobs 0` 表示每局比赛一个独立进程并行运行。输出双方胜局、平局、提前停止局数、平均手数和每局明细。用 `--no-alternate-colors` 可以固定第一方执黑；用 `--jobs 1` 可以改回串行评测。

## Minimax 与并行化背景

本项目中的 `alpha-beta` 可以理解为 minimax 搜索的剪枝版本。

minimax 是双人零和、轮流行动、完全信息游戏里的基础搜索思想。轮到己方时，搜索会选择让局面评分最大的走法，也就是 `max`；轮到对手时，假设对手同样理性，会选择让己方评分最小的走法，也就是 `min`。搜索到固定深度或终局后，算法用局面评分函数给叶子节点估分，再把这些分数一层层回传到当前局面，最后选出当前能保证的最好落子。

alpha-beta pruning 是 minimax 的剪枝优化。它维护两个边界：`alpha` 表示己方当前已经能保证拿到的最好下界，`beta` 表示对手当前能把己方压到的最好上界。当搜索发现 `alpha >= beta` 时，说明这个分支继续搜下去也不会改变上层选择，可以提前跳过。

在候选走法、搜索深度和评分函数完全相同的前提下，alpha-beta 与普通 minimax 会得到相同的最终选择；区别是 alpha-beta 通常会少搜索大量节点。也就是说：

```text
alpha-beta = minimax + 剪枝
```

当前 `alpha-beta:v1` 到 `alpha-beta:v4` 都属于这条 minimax 系路线。它们的核心决策语义一致，差异主要体现在候选点生成、棋型评分、Zobrist 缓存、置换表、make/undo、增量候选前沿和增量评估等工程优化上。

搜索资料中确实存在分布式或并行版本，常见名称不是单纯的 “distributed minimax”，而是 parallel/distributed game-tree search 或 parallel alpha-beta。代表方向包括：

- Distributed Tree Search：把树拆给多个处理器搜索，并把 alpha-beta 应用到 Othello 搜索中；典型难点是并行分支可能搜索到本可被串行边界剪掉的节点。参考：[Ferguson 和 Korf, 1988](https://cdn.aaai.org/AAAI/1988/AAAI88-023.pdf)。
- Young Brothers Wait Concept（YBWC）：先搜索最有希望的第一个子节点，拿到更有用的边界后再并行搜索兄弟节点，降低无效搜索。参考：[Feldmann 等, 1989](https://journals.sagepub.com/doi/10.3233/ICG-1989-12203)。
- ABDADA：明确以 “Distributed Minimax-Search” 命名的松同步分布式 alpha-beta/minimax 方法，通过置换表信息控制并行搜索。参考：[Weill, 1996](https://journals.sagepub.com/doi/10.3233/ICG-1996-19102)。
- APHID：异步并行 alpha-beta/game-tree search，适合在已有顺序搜索程序上较低侵入地增加并行搜索。参考：[Brockington 和 Schaeffer, 2000](https://www.sciencedirect.com/science/article/abs/pii/S0743731599916003)。
- TDSAB：把 transposition table driven scheduling 扩展到双人博弈搜索，把工作调度和置换表位置绑定，减少分布式置换表访问成本。参考：[Kishimoto 和 Schaeffer, 2002](https://webdocs.cs.ualberta.ca/~jonathan/publications/parrallel_computing_publications/icpp02kishi.pdf)。

当前仓库已经在 `gomoku-eval` 层面做了并行：`--jobs 0` 表示每局比赛一个独立进程。但单手棋的 `choose_move(board)` 仍是单进程内搜索。下一步如果要加速单手棋，优先考虑 root-level parallel alpha-beta：主进程生成顶层候选点，把候选点子树分给多个 worker 搜索，再汇总最佳分数和落子。

这一路线比完整 ABDADA、APHID 或 TDSAB 更适合当前 Python 代码，也更容易保持确定性和测试边界。首版不共享 worker 之间的置换表，只把并行作为可选参数；等有基准收益后，再评估共享置换表、异步搜索或更复杂的分布式调度。

## 新增算法版本的约定

新增算法时遵循下面的路径：

1. 在合适模块中实现一个带 `choose_move(board)` 方法的玩家类。
2. 在 `gomoku_ai/players.py` 中注册算法家族名和版本号，并补充别名。
3. 在 `tests/test_players.py` 中覆盖工厂创建和标签显示。
4. 如果改变搜索、候选点、棋型评分或缓存，补充 `tests/test_ai.py` 中的行为测试。
5. 如果影响 CLI 参数或评测流程，补充 `tests/test_cli.py` 或 `tests/test_evaluate.py`。
6. 更新本文档和 README 中的算法摘要。

建议保留旧算法注册名，除非明确要删除。这样每一版都能通过 `gomoku-eval` 做稳定对比，而不是只能凭主观体感判断棋力变化。

## 后续候选方向

可以考虑的后续方向：

- 引入迭代加深和时间预算，让 GUI/TUI 高难度仍能保持响应。
- 给置换表增加容量上限、替换策略和命中率统计，避免长局缓存无限增长。
- 增加可选的 root-level 并行搜索，让单手棋在高深度时可使用多个 CPU 进程搜索顶层候选点。
- 增加开局库或常见定式。
- 增加更系统的战术搜索，例如连续冲四和 VCF/VC2 类型强制胜检测。
