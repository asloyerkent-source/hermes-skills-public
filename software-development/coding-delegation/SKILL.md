---
name: coding-delegation
description: Use when 要写/改代码脚本配置：派 Pi/Aider/Codex 干，主模型不手写+实测验收。
version: 1.0.0
author: Hermes
license: MIT
metadata:
  hermes:
    tags: [coding, delegation, pi, aider, codex, submodel, verification]
    category: software-development
    merged_from: [pi-delegation, pi-coding-agent, pi-hermes-review-loop, external-model-coding, coding-agent-tooling]
---

# 编码委派（Hermes 不手写代码）

> 本技能合并了 5 个重叠技能（2026-09-26）：`pi-delegation` / `pi-coding-agent` /
> `pi-hermes-review-loop` / `external-model-coding` / `coding-agent-tooling`。
> 它们原本都围绕同一条纪律，此处统一为一套工作流，深度细节在 `references/`。

## 触发

- 任何"写文件 / 写配置 / 写代码 / 写脚本 / 建 cron"类任务。
- 用户说"让 Pi 干""你别自己上手写""为什么又自己上""用 aider 改""DS 太贵了"。
- 凡涉及**新建或修改磁盘上的工件**，先想"派出去写"，不是自己手写。

---

# 一、工作流（每次照此走）

```
用户要写/改代码
    │
    ├─ 步0  能不能自己做？
    │        <50 行 + 纯标准库 + 一次性 → 可自己写（但仍要实跑）
    │        其他一切 → 必须派出去
    │
    ├─ 步1  选谁干？ → 看下面「执行体选型表」
    │
    ├─ 步2  派发（prompt 卫生 + 纪律）
    │
    ├─ 步3  验收（铁律：不盲信自报，实跑才算）
    │
    └─ 步4  回写踩坑 → 让下次不再犯（相互学习闭环）
```

## 步0：何时可以自己做

> **动手前先过 `execution-discipline` Round 1（查本地真相源 → 查已有结论 → 出 BRIEF）。**
> 调查结论锁进 BRIEF 后再派活；多文件或 >50 LOC 时先做 `execution-discipline` Round 2.5（依赖图 + 垂直切片）再拆给执行体。


| 情形 | 自己做？ |
|---|---|
| <50 行、纯标准库、一次性小工具 | ✅ 可以（如 `add_weekly.py`、plot、推送端） |
| 读文件 / 整理 / 归档 / 写 md | ✅ 可以（不算"写代码"） |
| 系统配置（daemon.json / yaml / .env） | ❌ **绝对派出去**（手写是翻车高发区） |
| 任何 .py / .sh / .json / .yaml | ❌ 派出去（哪怕只有 10 行） |
| 大 / 复杂 / 长脚本（≥50 行） | ❌ 派出去 |

> 用户原话：**"应该尽量让 pi 干代码，为啥老要自己上呢？"**
> 手写看似快，但本用户历史上手写 `daemon.json` 加错字段导致 docker 挂、所有容器停。

## 步1：执行体选型表

| 执行体 | 适合 | 调用 | 成本 |
|---|---|---|---|
| **Pi**（`~/.local/bin/pi`） | 写新代码 / 配置 / 文件；短平快执行 | `pi --provider <p> --model <m> -p "<task>"` | 付费 key，费用随 provider |
| **Aider**（`~/.local/bin/aider`） | **改已有代码** / 重构 / 精准编辑 | `aider --yes --message "<task>" <file>` | 实测 $0.00085/次 |
| **Codex**（`codex-cli`） | 复杂代码 / 深度推理 / 多文件工件 | `codex exec --sandbox workspace-write "..."` | DeepSeek 付费 |
| **GLM/DS API 直调** | 生成独立**代码片段**（不碰仓库） | `references/api-recipes.py` | 极低 |
| **delegate_task 子 agent** | 隔离长上下文 + 严格限定的"执行+产出"活 | `delegate_task` | 共享额度 |

### ⚠️ 选型的关键区分

- **写新东西 → Pi**；**改旧东西 → Aider**（Aider 用 diff 格式精准改，不膨胀上下文）。
- **短活 → Pi 稳**；**长活/调研活 → 子 agent 必翻车**（实测 10 次派发：Pi 4/4 成，子 agent 长任务 5/5 败）。
- **子 agent 只干"执行+产出"**，绝不让它去"调研/梳理/排查"——它一调研就钻牛角尖，实测慢 16 倍且零产物。
- 只要生成独立片段、不需动仓库 → 直接调 API 最便宜。

### 选语言：默认 Python，但「判据型」要重新想（2026-09-30）

本环境默认 Python（脚本/数据/配置/审计工具，效率最高），**这不是问题**。但有一类活例外：

| 判据型代码 | 例子 | 为什么不适合 Python |
|---|---|---|
| 检查器 / 扫描器 / 过滤器 | `skill_ref_lint.py`、`skill_product_audit.py`、脱敏器 | **每个分支都判错时它照样跑、照样不报错**，只有负样本能抓住 |

2026-09-30 实测：`re.M` 当 `pos` 传给 `search()`（第二参数是 pos 不是 flags），
三个分类分支全误判——**正样本通过、跑一百次也看不出来**。
这类 bug 在 Go/Rust 里是**编译错误**（类型不匹配当场拒绝）。

**选型判据**：
- 一次性脚本 / 数据处理 / 配置 → **Python**（对）
- **别人会依赖的判据型工具** → 要么强类型语言，要么**接受「必须写样本自测」的成本**
- 折中：留在 Python，但把自测写进代码（`if __name__ == "__main__"` 带样本），
  让它每次跑都验一遍，而不是靠记性

**优先级提醒**：语言选型是**第三位**。第一位是「有没有现成的」（今天手搓 frontmatter 解析器
就是个教训），第二位是「写完有没有测」。语言排最后。


## 步2：派发纪律（所有执行体通用）

1. **prompt 纯 ASCII**（英文 + 半角符号）。中文/emoji/中文引号/em-dash/箭头 会触发
   系统的「Confusable Unicode homoglyph」扫描，命令直接被拦。
2. **绝不在 `IP:端口` 后加句点**（写 `127.0.0.1:7890`，不写 `127.0.0.1:7890.`），
   否则触发「Trailing dot in hostname」扫描。
   > 或把 prompt 写进文件再 `-p "$(cat prompt.txt)"`，隔离终端转义。
3. **给绝对路径**：`$HOME/.hermes/config.yaml`，不能只写 `config.yaml`
   （实测 Pi 改到了 `$HOME/config.yaml`）。
4. **喂事实、限范围**：已知事实直接写进 prompt，明令"不要查 X / 不要 grep Y"。
5. **任务书按八要素自查**（目标/输入/输出/约束/禁止改动/验证命令/验收标准/原始需求）。
   **照 `references/scenarios-strengths.md`（本技能自带） 里对应场景块逐条对照，缺就补。**
   场景块（软件开发/数据分析/文档写作/表格处理…）已把硬要求写死，照抄即可。

   ⚠️ **别用它的 `--analyze` 分数当判据**（实测 2026-10-01：空泛请求 25 分、补齐八要素 41 分、
   中等请求 42 分 —— **补齐反而更低**，且只认中文关键词，英文任务书 0 命中）。
   **那个分数只认中文关键词表，不是真的质量分。** `references/scenarios-strengths.md` 才是可用的。
   给"产出规格"而非"调研指令"。
5. **串行派活，不并行**——并行会打爆共享模型额度（实测 429 后子 agent 零产物却报 completed）。
6. **派 Pi 活前先探活**：`scripts/pi_probe.sh`（本技能自带，默认两轮；库外同款在
   `~/.hermes/scripts/pi_probe.sh`，两处内容一致，改一处要同步另一处）。
   别凭 `models.json`
   猜可用性——那是**账户状态**，配置里看不出来。实测四种失败长得完全不一样：
   - `429 rate_limit_reached_error` = **瞬时限流**，等几分钟自愈（实测 Kimi 连续 3 次 429，几分钟后 4s 就通了）
   - `429 + code 1113 / 余额不足` = **欠费**，等多久都没用，要充值
   - `403 AllocationQuota.FreeTierOnly` = **免费额度耗尽**，加钱或控制台关「仅用免费层」
   - `404 not found` = 模型下架，这条才该删配置

   **死条目不等于 key 该删**：2026-09-30 实测 glm-5.2（欠费）和 qwen3.7-plus（免费额度尽）
   都是账户问题，key 本身有效，充值/关免费层就恢复。删 key 等于放弃零成本恢复。

   **单次探活定生死必然误判**：qwen3.7-plus 第一轮测是活的（回了「活着」），几分钟后 403。
   所以脚本默认两轮，且「任何一轮成功过就算活」。

   **给「长任务」加 `timeout`**：探活能回一句话 ≠ 能跑完长任务。实测 qwen3-max 探活 3s 正常，
   但审查任务跑 25 分钟 0 字节输出（非交互模式输出缓冲 + 可能真卡）。`timeout 1500` 封顶，
   超时换模型重派，别无限等。
7. **涉敏感文件先备份**：`.env` / `config.yaml` 类任务的 prompt 必须含
   `cp <file> <file>.bak.$(date +%Y%m%d_%H%M%S)`（实测 Pi 曾用 `cat >` 覆盖 .env，丢掉全部 key）。
8. **长任务用 `background=true, notify=true`**，前台 `timeout=180` 不够。

### 派发前要素体检（任务书八要素）

派活前对任务书过一遍，缺哪项补哪项。**这是检查表不是模板** —— 别把这张表原样发给执行体。

| # | 要素 | 判据 |
|---|---|---|
| 1 | 目标 | 首句动词开头、一句话可检验 |
| 2 | 输入 | 输入文件的**绝对路径** + 表结构/格式 |
| 3 | 输出 | 输出文件的**绝对路径** + 格式 + 命名 |
| 4 | 约束 | 技术栈/版本、允许改动的范围 |
| 5 | **禁止改动** | 明令不许碰的文件/目录（例：`do NOT touch $HOME/.hermes/config.yaml`） |
| 6 | 验证命令 | 执行体自己该跑的校验（`py_compile` / 真跑一条 / diff 基线） |
| 7 | **验收标准** | 什么算过：期望输出、行数守恒、字段完整性、退出码 |
| 8 | 原始需求 | 用户原话（事后核对用，不翻译不改写） |

> **第 5、7 项是 2026-09-27 补的**：原派发纪律只有技术栈/路径/验证命令/备份，缺
> "禁止改动范围"和"验收标准"，导致执行体自由发挥边界、验收靠 Hermes 事后补。
> 来源：八要素内核（B 类）（多模型审后只保留了这一条内核）。

### ⚠️ 语言硬前置：发给执行体的 prompt 一律纯 ASCII 英文

第 1 条（纯 ASCII）是**不可协商的**，且与任何"提示词优化"工具的默认行为直接冲突：

- 铁律："输出语言与原始提示词一致" → 中文派活产出**中文任务书**
  → 发给 Pi 直接被 homoglyph 扫描拦掉。
- **正确接法**：优化器只用于 Hermes **内部**把口语补全成八要素（中文、内部思考）；
  真正发给 Pi/Codex 的 prompt 由 Hermes **重写成纯 ASCII 英文**。
- 中文原件（用户原话）只放**文件**里随附，**绝不进命令行参数**。

## 步3：验收（铁律：不跑通不算完）

### ⚠️ 判据型代码（检查器/扫描器/过滤器）必须跑 ≥3 组样本自测

2026-09-30 铁律。**"跑通"对判据型代码是不够的**——它能跑、没报错、输出看着对，
但可能每个分支都判错，而这种情况在你没写负样本时**永远测不出来**。

**三类样本各来一组：**

| 样本类 | 是什么 | 抓什么 |
|---|---|---|
| **正样本** | 确实该命中的 | 基本功能 |
| **负样本** | 确实不该命中的 | **误报**（最常见的失败模式） |
| **变体** | 形态不同但同类（块标量 vs 单行、大小写、边界值） | 只测了一个分支 |

**必须先拿库里的已知合规样本当对照组**，别自己造——自己造容易造出一个"恰好绕过缺陷"的样本
（铁律 18 的原话：变体样本从库里现取，找几个已知合规的技能当对照组，比自己造可靠）。

**今天的实测（skill_product_audit.py 的 classify_size）**：
只跑正样本时，"真胖"分支通过 → 我以为写好了。补 5 组样本后发现两个真 bug：

1. **`search(txt, re.M)`** —— `search` 的第二参数是 `pos` 不是 `flags`，
   `re.M`(=8) 变成"从第 8 个字符开始找"，三个分支全误判成同一类。
   **这类 bug Python 不会报错，跑一百次都看不出来**（若用 Go/Rust 写，编译器当场拒绝）。
2. **自测数据本身写错** —— 样本 size 写得比实际字节小，`size > ceiling` 不成立，
   函数按设计返回空串，却被我判为"失败"。**是自测不对，不是代码不对。**
   所以自测报错时，**先怀疑样本**。

**推论：Python 写判据型代码没有第一道防线。** 解释型语言不拦你，编译器会。
真想要这层防线，判据型工具该用强类型语言——但更实际的做法是**把样本自测写成硬约束**，
因为它对任何语言都成立。

**通用判据**（三选一即算失败，别自欺）：
- 断言名里带「不变 / 相同 / 未被写入 / 无变化」→ 体内必须有**前后两次取值**，不是 `size > 0`
- 声称「缺 X / X 不存在」→ **先打开原文确认 X 真缺**，再怀疑检查器
- 声称「修好了 / 全部通过」→ 先在**没改之前**跑一遍，看基线数字

- [ ] **读真文件**确认内容（不只读它自报的 "done"）
- [ ] **语法/格式校验**：`py_compile` / `bash -n` / `dockerd --validate`
- [ ] **真跑核心命令**看结果是否如它所述（不轻信 `--help` 或它粘贴的输出）
- [ ] **判据型代码**：≥3 组样本（正/负/变体），负样本必须有（见上）
- [ ] **改配置后 `diff` 对比**，确认无意外回退
- [ ] **基线对比**：`md5sum <不许动的文件>` + `git status --porcelain`

> ⚠️ **离线自测绿 ≠ 能用**。agent 只能跑它自己的纯逻辑自测，**运行时取值类缺陷它抓不到、
> 也不会承认**。Hermes 必须自己写探针驱动集成接缝、真跑一次端到端。
> 两轮才修完是常态：发现缺陷 → 写 FIX BRIEF（含复现证据/根因/改法/验证命令）→
> **派回同一个 agent**，不让主对话变成手写代码。

## 步4：回写踩坑（相互学习闭环）

Pi 不是一次性工具，而是**能力随任务增长的长期副手**。闭环：

1. Pi 写/改代码
2. Hermes 多模型审（DeepSeek 主审 + 其他二审）挑**真缺陷**
3. **回写 `~/.pi/agent/AGENTS.md` 的「踩坑记录」段**（格式 `日期: 问题→修复→教训`）
   → Pi 下次启动自动读，规避同类错。**这步不能省**，漏了 Pi 下次还犯。
4. 派 Pi 自修 → 读码验证它真改对

> ⚠️ **Pi 自身文件禁止为"优化"改动**（`AGENTS.md` / `models.json` / bundle）。
> 用户两次叫停"Pi 不要动"。token 节省走 Hermes 侧或派活 prompt 层。
> **回写 `~/.pi/agent/AGENTS.md` 的「踩坑记录」段是唯一例外**（用户授权的学习载体）。

---

# 二、五条铁律

1. **配置/代码一律派出去写**，Hermes 不手写（即使 10 行）。
2. **Hermes 只做**：派任务 → 收产出 → 实测验证 → 回写坑。
3. **不盲信任何自报**。Pi / 子 agent / Codex 的 "done/统计/结论" 一律当假设，
   用 `rg` / `wc -l` / 真跑命令独立复算后再采纳。
   （实测：Pi 报"Kimi key 失效 401"，实为 config 缺 provider；报 3302 个碎片，实为 2273。）
4. **指定 agent 必须真调**。用户点名 Pi / Codex / Claude Code 时，必须真的调用它；
   没跑通就说"没跑通"+报错。**自己读文件审一遍不算执行**——那次派发本身就是交付物。
5. **纯调度 / 跨机 / 真相源 / 破坏性操作拍板**才 Hermes 上。

---

# 三、各执行体速查

| 执行体 | 安装/配置 | 坑与细节 |
|---|---|---|
| Pi | → `references/pi-setup.md` | → `references/pi-pitfalls.md` |
| Aider | → `references/aider-codex-setup.md` | 同上 |
| Codex | → `references/aider-codex-setup.md` | 同上 |
| GLM/DS API | → `references/api-coding.md` + `references/api-recipes.py` | → `references/model-quirks.md` |

**选型与成本**：→ `references/tool-selection.md`
**多模型审核 + 相互学习**：→ `references/review-loop.md`
**派发事故案例（必读）**：→ `references/delegation-discipline.md`
**生态清单（推荐新工具前先看）**：→ `references/coding-agent-landscape.md`

---

# 四、参考文件

- `references/delegation-discipline.md` — 派发纪律详解 + 真实事故案例（误删 16 视频、并行打爆额度、开放调研磨蹭 10 分钟）
- `references/pi-setup.md` — Pi 安装、models.json、多 provider、调用模板
- `references/pi-pitfalls.md` — pi-lens 改写 md、.env 覆盖、范围发散、prompt 扫描、模型幻觉、自我保护
- `references/pi-extension-api.md` — Pi 0.87 扩展 API 契约（parameters/execute/返回值，旧 API 会导致 Pi 整体拒启）
- `references/aider-codex-setup.md` — Aider 安装/后端（含 z.ai 停用后切 DeepSeek）、Codex 状态与 AppArmor 修复
- `references/api-coding.md` — GLM/DS 直调流水线、拆函数防截断、拆装坑、模型池与 fallback 链
- `references/api-recipes.py` — 可调用代码：`call_glm` / `call_ds` / `extract_code`
- `references/model-quirks.md` — 各家模型长输出/截断实测行为表
- `references/tool-selection.md` — 工具对比、DS 真实单价、选型纪律
- `references/review-loop.md` — 多模型交叉审核阵容 + Pi↔Hermes 相互学习闭环
- `references/coding-agent-landscape.md` — 已安装/待评估的 coding agent 清单
- `references/long-process-background-run.md` — 长进程被 SIGKILL 的根因（cgroup）与修法
- `references/env-file-write-restrictions.md` — .env / config.yaml 等敏感文件的写入限制

- `references/local-coding-agents.md` — 本地/离线 coding agent 清单与实测（原文保留）
- `references/agent_self_evolution_engine.md` — Agent 自演化引擎：把经验蒸馏成原则，**记忆≠智慧**
- `references/aider_windows_template.md` — aider + GLM 在 Windows/MSYS 的调用模板与三个坑（PyPI 空壳包 / xterm 冲突 / `ZAI_API_KEY`）
- `references/aider_glm_template.bat` — aider+GLM 精准编辑封装脚本（含已踩的坑）
- `references/ds_cost_math.md` — DS 成本反推：2026-08 真实账单逐时段换算

---

# 五、相关但不属本技能

以下内容原先混在 `pi-delegation` 里，已按主题拨开（各自有更合适的归属）：

| 原章节 | 新归属 |
|---|---|
| QQ Bot 接入 5 坑 | → `references/displaced-qqbot-and-misc.md`（待迁到 qqbot/gateway 技能） |
| mihomo 微信代理修复 | → 同上（待迁到 `network-management-system`） |
| TokenTracker 监控 | → 同上（待迁到 `model-logging`） |
| 本地算力现实（P620/Whisper） | 已有 skill `local-vlm`（原 `local-vlm-3046`） |
