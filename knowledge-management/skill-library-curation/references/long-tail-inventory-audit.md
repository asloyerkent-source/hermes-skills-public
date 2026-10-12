# long-tail-inventory-audit — 原技能正文（逐字）

> 2026-09-26 「技能管理簇」5→1 合并：本文件逐字并入源技能 `hermes-skill-inventory-audit` 的 SKILL.md 正文（去 frontmatter）。
> 源目录 `devops/hermes-skill-inventory-audit/` 已归档于 `.archive/hermes-skill-inventory-audit/`，原件逐字保留。

## ⚠️ 口径修正（后补，**优先于下面的历史结论**）

### `.usage.json` 不能单独用来判「没用」

`.usage.json` 记的是 **agent 载入事件**（`skill_view` / 自动加载），**不记脚本直跑、也不记 cron 调用**。
实测：一批标着「从未使用」的技能里，包含**当天真被跑过脚本**的（本地决策、提示词优化器）
和被别处引用十几次的。**`use_count: 0` 不等于没用。**

### 判「该不该删」必须三信号交叉，缺一不可

| 信号 | 取法 |
|---|---|
| agent 载入 | `.usage.json` 的 `last_used_at` / `use_count` |
| **被引用** | 活动树里搜**精确形态**：反引号 `` `name` ``、`skill_view('name')`、`<name>`（跨技能正文与 frontmatter） |
| **可执行物** | 技能内有无 `scripts/`；是否被 `cron/jobs.json` 提到 |

判据：**零引用 + 零脚本 + 无 cron + ≥24 天未改**才够格当淘汰候选；
只要有脚本或被他处引用，即使 `use_count: 0` 也**不能删**。

### ⚠️ 「缺 X 的百分比」是危险指标（2026-10-10 实测）

初版报告算出「61/89 = 69% 的技能缺否定边界」，看着很严重。逐条查证后
**真缺口只有 4/89 = 4.5%**——因为否定边界**只在有易混兄弟技能的家族内部才有意义**：
有边界的 18 个技能（安全审计三件套 / 网关排障 / 技能治理 / 双机）**全部**有易混邻居；
而 `github` / `china-briefing` / `commodity-price-tracking` 这类独苗根本不需要。

**百分比把「不需要 X 的」也算成了「缺 X」**，会推着人去做几十个无用改动。
**先问「谁真的需要 X」，再数**；报缺口前逐条过一遍「这一条真需要吗」。

两个比百分比可信的实证判据：
- **使用/载入比**（全库汇总 `use_count / view_count`）：≈1.0 说明载入的都真用上了、
  **无误触发实证**；远小于 1 才说明有技能被载入却没派上用场。
- **回归测试**：`scripts/skill_trigger_regression.py` 跑真实话术；全过 = 触发词没缺。
  注意它只测**描述可读性**，不是唤醒率——别把输出当更大的结论用。

同理，排查「引用断链」时要区分**真断链**与**正文里的示例路径**
（如讲解依赖图时写的 `../site-packages/`）：后者是误报，改它反而破坏说明。
批量导入的外部技能包常带 `../tool-index.md`、`../field-journal/` 这类本机不存在的兄弟路径，
那是真断链，修法是删步骤或改指向本机存在的技能。

### 补描述时的硬约束：边界要在 60 字符内

`description` 超 60 字符会被索引截断（`skill_repo_doctor.py` 报 `description 61 字符 > 60 上限`），
**边界写在后面等于没写**。写法：把边界压短、放句尾，如
`（全栈体检交health-check）`；并同批重建 INDEX（`scripts/register.sh`）后重跑体检确认。

### 长尾候选里的大头是「还没合并的簇成员」，不是死重

一批「零引用」技能逐条读下来，多数属于尚未合并的同类簇。
**先比对本轮簇队列，能合并就别删**——删除是最后手段，合并才是主路径。

### 保护标记扫描有假阳性，必须逐条读原文

`grep -rniE 'sacred|never merge|禁止合并|不可合并|别删'` 命中即出队，
但命中的常是文档里的无关句子（描述某个文件 "never deleted" 的行为、某个模板的 "never delete" 用法）。
真命中（如「敏感档案硬隔离：家属纪念照片、基因数据」）**必须原样保留其约束语义**，
合并进别的技能时不许改写成弱表述。

---

> ⚠️ 下面「可删 / 需要读取 / 介意保留」三张表是**某次审计的历史快照**，
> 其中技能名、分类与体积多数已过时（技能已合并、更名或归档）。
> **不要照着这些表动手**——按上面的三信号口径重新扫一遍。

# Hermes Skill 清理审计

## 背景

user（浩哥）：定期检查一遍全部 skill，找出 7天以上没在用的，确认该不该删。

## 审计原则

### 1. 不可盲删原则

- **删之前读 SKILL.md**——用处/产物写在那儿。
- **空目录≠可删**——有的空目录是安装残留/占位，发送删除要和 user 确认，再删。
- **含有工作脚本/测试用例/产物的 skill，先确认掉了没再考虑删**。

### 2. 判定「最近用了没」的代理

- 最佳代理：**脚本产物的最后生成时间**（json/metrics/reports/essence），而非 skill 目录本身的 mtime。
- 次要代理：skill 内文件最近一次 mtime（比目录 mtime 强）。
- skill 文件 mtime 也可作为代理——但她可能仅是安装/更新时的写入，不代表使用。

### 3. 处理层级

1. **活跃的（≤7天最新的有内容变动/产物）：保留，不碰**。
2. **「可能仍有用」的（近 30 天内有活动，或用途不明但文件丰富）：先读 SKILL.md 再动，必要时问 user）**。
3. **长期不动 + 证据薄弱（≥7天无活动，且 SKILL.md/产物都空或无用）：可以删，除非 user 保留）**。

## ⚠️ 关键教训：mtime 不可信，且「已合并」声明大多是假的

### 教训 1：skill 目录 mtime ≠ 使用

约 50 个 skill 的 mtime 全是同一时刻（某次批量移动），完全不能拿来判断"有没有在用"。
**不要凭 mtime 提议删除。** 真能看的信号：
- skill 内脚本产出的**产物**最后生成时间（日志/json/report）
- 真不确定就**问用户**，不要猜

### 教训 2：磁盘顶层目录 ≠ skill 列表

**三个 skill 根目录**，必须全扫：
- `~/.hermes/skills/` —— 主库
- `~/.hermes/hermes-relay/skills/` —— relay 插件自带（doctor/status/pair/self-setup/desktop-setup/troubleshooting）
- `~/.agents/skills/` —— obsidian-cli/markdown/bases、json-canvas、officecli、defuddle

只扫主库会误判"skill 不存在"。

### 教训 3：删占位目录前先查 hub 清单

`.hub/index-cache/official_optional_dirs.json` 是官方可选目录清单。
在清单里的分类目录 **删了会被 hub 自动重建**（症状：删完过几分钟又出现，只剩一个 DESCRIPTION.md）。
不在清单里的（如 `github`/`openclaw-imports`/`wondelai`）删除后才真消失。
这类占位目录不加载成 skill（无 SKILL.md），留着无害，不值得跟 hub 较劲。

### 教训 4（最重要）：先验证「已合并至」是真合并还是只贴了标签

本次发现 **28 个 skill 挂着假合并声明**：顶部写着
`> 已合并至 X，本文件保留为指针。`
**但正文原封不动全在**，且目标 X 里根本没有这些内容。

**验证方法（必做，不能只看那行声明）**：
1. 提取源文件正文的**有效行**（去空行/标题/引用行，长度≥25 字符）
2. 归一化空白后在目标文件全文里找
3. 计算覆盖率：
   - **覆盖率 ≥80%** → 真合并，源文件可删
   - **40–80%** → 部分重复，需先补全目标再删
   - **<40%** → **目标里没有内容，源文件绝不能删**
4. 再查目标里有没有**反向引用**源 skill 名（有引用 = 有意的枢纽式设计）

本次实测 28 个指针里，覆盖率绝大多数是 **0–18%**，反向引用几乎没有——
即上轮"合并"只贴了个标签，内容从没搬过去。
**若轻信那行声明就删源文件，会直接丢内容。**

### 教训 5：断链指针

指针指向的目标可能已被归档到 `~/.hermes/skills/.archive/`。
归档的 skill **不会被加载**，所以这类指针等于指向虚空。删除前务必验证目标是否在活动根目录里。

### 教训 6：冗余是两层的——skill 本体 + `references/` 副本

之前的"合并"实际做法是：**把原 skill 内容复制成 `<hub>/references/<name>.md`**，原 skill 不删。
所以同一份内容可能同时在两处。查重时必须两层都扫。

### 教训 7：hub 里的 reference 副本可能没被链接（致命陷阱）

**删原 skill 前，必须验证 hub 的 SKILL.md 真的引用了那个 reference。**
本次实测：
- `coding-agent-tooling/SKILL.md` 链接了 2/4 个 references（`ai-coding-agents.md`、`local-coding-agents.md` **未链接**）
- `pi-delegation/SKILL.md` 链接了 2/4 个（`submodel-codegen.md`、`external-model-coding.md` **未链接**）

> 2026-09-26 更新：这 5 个编码 agent 技能已合并为 `software-development/coding-delegation`，
> 本节仅保留为历史审计记录。孤儿 references 的教训已并入
> `hermes-skill-inventory-audit/references/` 或 coding-delegation 自身。

**未链接的副本 = 孤儿**。此时删原 skill 会让内容彻底无法被发现。
正确顺序：**先把 reference 加进 hub 的「## 参考」区，再删原 skill**。

### 教训 8：YAML frontmatter 里的 `: ` 会炸

`description: 双机/多机Hermes互联运维: 连接建立...` —— 中文描述里的**冒号+空格**
会让 YAML 当成嵌套映射，报 `mapping values are not allowed here`。
**修法**：整个 description 加双引号。
批量体检：对所有 SKILL.md 跑 `yaml.safe_load`，别等出事。

## 合并操作 SOP（安全顺序）

1. **读全文**（源 + 目标），列出源的独有章节
2. **写合并版**（重写去重，保留全部独有内容）
3. **搬引用文件**（源 references/ 里目标没有的）
4. **验证覆盖度**——源的有效行逐条在合并版里能找到（语义级，重写不可能逐字匹配）
5. **归档源，不硬删**：`mv <src> .archive/<src>-merged-into-<dst>`（可反悔）
6. **查残留引用**：`grep -rl <src> <活动目录>`，更新指向它的地方
7. **全量体检**：跑 frontmatter YAML 校验 + 确认 skill 数没异常

## 可删——证据薄弱 / 长期不动

（以下基于 2026-09-26 审计，间隔用的是文件改动 mtime 代理。）

| skill | 最后动的时间 | 间隔 | 评估 |
|---|---|---|---|
| email | 55天前 (08-01) | 55天 | 1文件0KB，空目录级别，可删 |
| github | 55天前 (08-01) | 55天 | 1文件0KB，空目录级别，可删 |
| apple | 24天前 (09-01) | 24天 | 1文件0KB，可删 |
| autonomous-ai-agents | 24天前 (09-01) | 24天 | 1文件0KB，可删 |
| creative | 24天前 (09-01) | 24天 | 1文件0KB，可删 |
| media | 24天前 (09-01) | 24天 | 1文件0KB，可删 |
| social-media | 24天前 (09-01) | 24天 | 1文件0KB，可删 |
| web | 24天前 (09-01) | 24天 | 1文件0KB，可删 |
| openclaw-imports | 从未动过 | 从未 | 空目录，可删 |
| wondelai | 从未动过 | 从未 | 空目录，可删 |

## 需要读取 SKILL.md 再决定

| skill | 最后动的时间 | 间隔 | 文件数/大小 | 建议 |
|---|---|---|---|---|
| hermes-hud | 16天前 (09-10) | 16天 | 153文件 / 4.1MB | 装了一半的 Dashboard 项目，重装可能费时，**删前读 SKILL.md** |
| automation | 20天前 (09-05) | 20天 | 6文件 / 17KB | 可能包含 cron-notify 等，可删前读 |
| file-management | 23天前 (09-02) | 23天 | 8文件 / 25KB | 安装类，一次用可能够了——**读 SKILL.md 后再删** |

## 介意保留 / 活动类型不明确

（都是触发型/元技能/安装型，不适合仅凭目录 mtime 来删。）

| skill | 最后动 | 评估 |
|---|---|---|
| knowledge-management | 8天 | vault 整理使用触发型 |
| note-taking | 8天 | 同 |
| mlops-inference | 8天 | 同 |
| windows | 8天 | 同 |
| hermes | 8天 | Hermes 本体相关 |
| connectors | 3天 | 连接类 |
| productivity | 2天 | 生产力脚本如价格追踪/voice transcription |
| research | 10天 | 资讯监控 |
| archive-hygiene | 8天 | 文件归档类 | ⚠️ **2026-09-27 已并入 `file-management/safe-file-organization`**（归档在 `.archive/`） |
| safe-delete-trash | 8天 | 删除保护 | ⚠️ **2026-09-27 已并入 `file-management/safe-file-organization`**（归档在 `.archive/`） |

## 活跃（≤1天，保留）

devops, flows, hermes-ops, mlops, model-logging, software-development, skill-review-session-20260926, 等等——这几天有在动，直接保留。

## 执行摘要

**可以删的（清理候选）**：email, github, apple, autonomous-ai-agents, creative, media, social-media, web, openclaw-imports, wondelai —— 以上都是空/占位目录或长期不动且无产物。

**删前读 SKILL.md 的**：hermes-hud, automation, file-management.

**保留的（活动型/触发型技能）：** knowledge-management, note-taking, 以及活跃目录里的其他技能.

## 重装代价

若删错了，需要再装：按 skill 来源不等——有的从 GitHub 拉，有的手写 SKILL.md，有的有关联技能/模型绑定。删之前要有后悔的准备，或者给 user 选择。
