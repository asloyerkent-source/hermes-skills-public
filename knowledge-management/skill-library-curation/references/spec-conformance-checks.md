# spec-conformance-checks — 技能格式体检（11 项 100 分制）

> 工具：`~/.hermes/scripts/skill_spec_audit.py`（Python 3 零依赖）
> `python3 ~/.hermes/scripts/skill_spec_audit.py ~/.hermes/skills [--json] [--single <dir>]`
> 规则移植自 `@skilldex/<EMAIL>`（MIT, Pandemonium-Research/Skilldex）。
> 原仓库只含 I/O 层（找目录/读文件），**评分规则在另一个 npm 包里** —— `npm pack @skilldex/validator` 才拿得到，纯 JS 未混淆可读。

## 这套检查答什么、不答什么

**答**：格式是否合规（能不能被正确解析/触发/维护）。
**不答**：功能是否重叠、是否适合本机使用者、内容质量。
**格式分 100 不等于技能好** —— 权重里 `content quality` 是 0 分。报告要照实说这一点，
否则「平均 84.9 分」会被读成「库很健康」，而它只说明**结构**健康。

## 权重表（单一来源，分数/明细/显示都读它）

| 检查项 | 权重 | 判什么 |
|---|---|---|
| frontmatterParseable | 16 | YAML 能解析 |
| namePresent | 16 | 有 `name` |
| descriptionPresent | 16 | 有 `description` |
| nameFormat | 11 | kebab-case、不含保留词（claude/anthropic） |
| descriptionFormat | 11 | **说明了触发场景**（`Use when` / `触发`） |
| lineCount | 7 | ≤500 行（>400 警告） |
| referencedResourcesExist | 7 | **引用的 `references/`、`scripts/` 文件真实存在** |
| descriptionLength | 6 | ≥30 词、≤1024 字符 |
| allowedSubdirs | 4 | 只允许 `scripts/` `references/` `assets/` |
| noReadme | 4 | 目录内不应有额外 `README.md` |
| bundledResourcesCorrect | 2 | `scripts/` 下不该放文档 |

两个设计要点值得保留：

- **单一权重表**。分数、逐项明细、显示读同一张表 —— 明细不可能与总分漂移。
  原作者自述教训：曾把分值写在注释里，**3 处漂移、1 处写着「25 分」实为 16 分项**。
- **静默 ≠ 跳过**。某项通过时不发诊断，但确实跑过并给了分；
  只有「既未给分也未发诊断」才是真跳过（依赖项先失败）。这个区分要保留，
  否则「0 条诊断」会被读成「什么都没查」。

## 阈值（来自原实现，按需调整）

```
MAX_LINES=500  WARN_LINES=400  MIN_DESCRIPTION_WORDS=30  MAX_DESCRIPTION_CHARS=1024
ALLOWED_SUBDIRS={scripts,references,assets}  RESERVED_NAME_WORDS=[claude,anthropic]
```

`MIN_DESCRIPTION_WORDS=30` 对中文技能偏严（中文按空格分词，30 词≈很长一段）。
报出「description 太短」时先看该技能是否已用 `触发：`/`Use when` 表达触发条件 ——
**那才是 descriptionFormat 真正要抓的东西**，长度只是代理。

## 自己写 frontmatter 解析器的三个坑（都实测踩过）

手搓 YAML 解析器时，逐字对照过以下失败模式：

1. **块标量内容行不以 `key:` 开头**。先试匹配 key 再判「是否在块内」，
   合法的 `description: |` 正文会被当成「无法解析」。**顺序必须反过来**。
2. **`cur_list` 与 `fm[key]` 必须是同一个对象**。
   写成 `cur_list, fm[key] = [], []` 是两个不同 list —— append 进前者、定型时从后者 join，
   结果永远空（表现为「description 缺失」）。
3. **块标量定型要在离开该块的那一刻做**。推到循环末尾会失效，
   因为 `cur_key` 已被下一个顶层 key 覆盖。

块标量两种写法都要支持：`|`（字面块，保留换行）与 `>`（折叠块，换行折成空格），
外加 chomping 变体 `|-` `>-` `|+` `>+`。

## 自检：单样本通过不算通过

只用一个「单行 description」样本验证解析器会漏掉整个块标量分支。
**最少验三类样本：单行值 / `|` 块 / `>` 块**，再加一个空 `description:`。
每类各取库中一个已知技能对照 —— 声称「缺 description」的技能，要先打开它的
frontmatter 亲眼确认，再决定它是真缺还是解析器坏了。

## description 过长会被索引截断——但先分清「硬上限」和「路由信号上限」

两个不同的阈值，机制不同，处置也不同：

- **创建时的硬上限**：新建技能的 description 超过约 60 字符会被工具直接拒。
  这是**创建期**的门，拦住的是「新写的技能」。
- **运行期的信号上限**：技能索引会把 description 截断后展示（实测截到 57 字符 + 省略号）。
  后果是**截断掉的部分里如果有触发词，它就永远不参与路由** —— 技能存在、能被 `skill_view` 读到全文，
  但「我想不起来去调它」。

所以「老技能 description 超长」不等于坏文件，只等于**它的路由信号被削**。
判据是**截断后剩下的那几十字里有没有可触发的说法**，不是总长度。

处置顺序：**先读全文 → 只把最前面压到能独立触发**（触发词前置，别改写含义），
不要为了凑字数把规则重写成另一种说法——那是拿可用性换合规。
超长到「前 57 字完全没有触发词」的那几个（实测有跑到 200+ 字符的）才值得优先改。

**不要用「统一压到 60 字」当批量处方**：很多老技能的 description 是多层职责叠出来的，
压掉的部分往往正是另一个触发场景。改之前先确认丢掉的那段不承担路由职责。

## 报「引用了不存在的文件」前先确认不是拼写差异

该检查抽 regex 抓正文里的 `references/...md` `scripts/...py` 路径。
它是有效的（实测抽样三个全部确认文件真缺失），但**它只看路径字符串**：
正文里作为「反面例子」写出的路径会假阳性。发现成片缺失时先 `ls` 几个确认，
而不是直接改技能。

## 覆盖范围

只扫 `<root>/<分类>/<技能>/SKILL.md` 与 `<root>/<技能>/SKILL.md`。
**装在根目录的技能**会被扫到，但**软链指向 `~/.agents/skills/` 的真身不在范围内** ——
那批要在 `config.yaml` 的 `skills.external_dirs` 里显式声明，或用工具自带的
`--extra-root` 补扫。漏扫的技能不报错，只是静默缺席，所以要与
`glob(**/SKILL.md)` 的个数对账。
