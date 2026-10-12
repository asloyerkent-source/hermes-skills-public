# structural-health-checks — 原 skill-library-curation/SKILL.md 第 95–129 行（逐字）

> 2026-09-26 「技能管理簇」5→1 合并：本节从主 SKILL.md 拆出，内容逐字未改。

## Structural health checks (run before any merge/delete)

The generated `INDEX.md` can be silently broken while still claiming the right total. Verify, don't trust:

```bash
cd ~/.hermes/skills
# rows that lost their leading pipe -> unparseable as table rows
awk 'NR>1 && $0 !~ /^#/ && $0 !~ /^>/ && $0 !~ /^\|/ && length($0)>0' INDEX.md | wc -l
grep -c '^## ' INDEX.md          # category headers; should equal the number of DISTINCT categories
head -5 INDEX.md                  # declared total vs actual file count
```

A healthy index has `#rows ≈ #skills` and `#category headers = #distinct categories`. Real observed failure: 219 skills rendered as 260 pipe-rows + 34 orphan rows under **119 category headers** for 11 categories — the generator re-emitted the category heading per batch and dropped the wrap pipes on continuation rows. Fix the generator (`skill-catalog/register.sh`), never hand-edit the generated file.

### Declared merges that never happened

A skill can carry a merge declaration in its own text (`> merged into X, kept
as a pointer`) while its body is fully intact **and X contains nothing from
it** — a label, not a merge. Trusting the declaration and deleting "the
pointer" destroys the only copy.

Verify coverage before acting: extract the source's non-blank lines and look
for each in the target.

```bash
src=... target=...
grep -vE '^\s*$' "$src" | while IFS= read -r l; do
  grep -qF -- "$l" "$target" || echo "MISSING: $l"
done | wc -l     # MISSING ≈ total lines  =>  the merge never happened
```

A 0–18% coverage rate means the declaration is fiction. The honest cheap fix
is to strip the declaration and leave the body intact; really merging is a
separate, larger job.

### Structure-pass debt: the concatenation fingerprint

A union merge that ran the content pass and skipped the structure pass leaves a
fingerprint you can grep for — the executor keeps each source document's own
opening line as a section header:

```bash
grep -rc '^## 源模块:' ~/.hermes/skills --include=SKILL.md 2>/dev/null | grep -v ':0'
```

Read the count together with the file size:

| 指纹数 | 体积 | 判定 |
|---|---|---|
| 1 | 正常 | 单一来源，只是留了溯源标题 |
| **≥2** | **远超上限** | **结构 pass 从未执行** |

Symptom set for a concatenated skill: size far over the ceiling (observed 9.9×
and 3.0× the 12288B limit), no navigation table, no unified heading language,
each source's own `Trigger:` / `## Why` still dangling inside the body.

**The size report cannot tell you this.** `skill_product_audit.py` flags the
overage, not its cause, and an overage from concatenation looks identical to one
from genuinely long content. Grep for the fingerprint before deciding whether a
big skill needs its *content trimmed* or a *structure pass done* — the fixes are
different, and only the structure pass is a re-ordering job the main context can
do cheaply. Run the same grep over `.archive/`, where a half-merged artifact can
sit unnoticed and get re-merged later.

---

### 断链/失效引用检查：路径形状的 token 不等于本技能内的路径

任何「引用了不存在的文件」检查器（自己写的，或现成 lint）都栽在同一处：
**正文里的 `references/x.md` 长得一样，作用域却完全不同。** 不先分类就查存在性，
得到的假阳性率高到让整个检查器不可用——而不可用的检查器比没有更糟，
因为人会开始忽略它的输出，包括真问题。

判据：**逐条读报出的那行的上下文，再决定是修文件还是修检查器。** 一次全假阳性的
批量报告是「检查器的路径解析有 bug」的指纹，不是「库里烂了」的指纹。

至少要分清这五类，只对第一类做存在性判定：

| 形态 | 例子 | 该不该报 |
|---|---|---|
| 技能内自带资源 | `` `references/guide.md` ``（相对本技能目录，且文件真不在） | **报** |
| 家目录/绝对路径 | `~/.hermes/scripts/watchdog.py`、`/opt/x/y.md` | 不报（要用 `$HOME` 解析后另判） |
| 跨技能引用 | `skills/<类>/<名>/references/a.md` 或正文里直接写另一个技能的 references 路径 | 不报（要用 skills 根解析后另判） |
| 代码块内 | ```` ```python\npython scripts/repro_bug.py\n``` ```` | 不报——这是读者**自己项目**的示例文件名 |
| 散文简写 | 「见 `agents/code-reviewer.md`」实为顶层 `agents/` 而非 `references/agents/` | 不报——先确认目录层级再下结论 |

后两类最隐蔽：代码块里的示例文件名**必然不存在**（它属于读者的仓库），
而散文里的简写路径**看起来完全合法**——只有把那一行前后各 200 字读出来才看得出它指向别处。
**没有上下文的路径存在性判定是纯猜测。**

实现上用**负向先行**过滤（先排掉四类不该收的形态，再收剩下的），比逐条加白名单稳：
跟踪代码围栏状态跳过块内行；命中 `~/` / `/` 起始的整行跳过；
命中 `skills/<类>/<名>/` 的整行跳过。反引号可有可无——两种写法在真实技能里都常见，
只认带反引号会漏掉一大半。

**收紧过头和没收紧一样糟**：只收带反引号的路径，会让裸写的合法引用全部消失，
真断链被一并掩盖。规则是「排掉明确不是本技能的」，不是「只认某一种写法」。

**现成脚本**：`~/.hermes/scripts/skill_spec_audit.py`（移植自 `@skilldex/validator`，
11 项 100 分制：frontmatter / name / description / 行数 / 子目录 / 引用资源）。
加新检查项时先读它 `collect_referenced()` 里那四条负向过滤，照着加，别重写。
⚠️ **`--single` 必须 `cd ~/.hermes/skills` 后传相对路径**（`--single flows/i-have-adhd`）；
传技能名或绝对路径都报「缺 SKILL.md」。这是调用姿势错，不是技能坏了——
拿到「缺 SKILL.md」先换路径再下结论。`--json` 全量输出可直接汇总分项。

### ORPHAN 报的宿主技能路径也可能是错的——先定位真宿主再改引用

ORPHAN 行给出的是「扫描时归到的技能」，不保证是文件的真实归属。
改引用前先 `find` 出真宿主，否则会把指针加到错的技能里，而真正的孤儿仍没接上：

```bash
find ~/.hermes/skills -name '<孤儿文件名>' -not -path '*/.archive/*'
```

**⚠️ 看着像垃圾的目录名别急着删**：`scripts/G:\\双机对接\\…` 这类 Windows 盘符名目录，
里面可能装着**有内容的对接文件**（给 Windows 侧脚本按字面路径读）。
先 `find . -type f | wc -l`，为 0 才是空壳；删除用 `rmdir` 逐层（`rm -rf` 误伤同目录真文件不可逆）。
实测同批里一个真空的 `H:` 盘符目录（3 层全空）和一个装着对接记录的 `G:` 目录长得一模一样。

### 「它超标了，那一定有冗余」——先量三个数，再谈砍不砍

对于**没有** `## 源模块:` 指纹的超标技能（即不是拼接体），最容易犯的错是「那就删点内容吧」。
先量下面三个数，都很便宜：

1. **文件内重复段落**——按 `^##` 切段，对 ≥120 字符的段落取 md5 查重，数重复条数。
2. **历史/变更类占比**——正则计日期 `20\d\d-\d\d-\d\d` 与词频 `修复要点|本轮|迁移|已弃用|legacy|旧写法`；
   某段这两个密度高到一定程度就归为历史类。
3. **跨技能共享实质行**——全库 73 个 SKILL.md 两两比，任何 ≥45 字符、非标题/表格/frontmatter 的行出现在 ≥2 个文件里。

实测五个超标技能（officecli 2.1× / knowledge-vault-ops 1.8× / model-logging 1.8× /
execution-discipline 1.6× / skill-library-curation 1.2×）：

| 指标 | 实测 |
|---|---|
| 文件内重复段落 | **0 条** |
| 历史/变更类内容占比 | **2%**（99554 B 里只有 2437 B） |
| 跨技能共享实质行 | **≤ 1 行** |

→ **0% 冗余、100% 结构债。** 唯一正确动作是拆 ref；此时砍内容一定错，
被删掉的会是独有操作规程。**把这三个数当作断言「某技能有冗余」的前置基线。**

### 超标本身不总是缺陷

两个**已知且有意**的例外，不要排进拆分清单：
- **sacred 技能**（`agent-communication-discipline`）——永不合并、永不裁剪。
- **被当作技能存放的第三方 git 仓库**（`flows/skill-evolution`，自带 `.git`/tests/uv.lock）——它是独立工具项目。

> ⚠️ **2026-10-01 已归档**：依赖 `gepa`/`fastembed` 缺失、无 cron 任务、126 次评估 0 采纳。
> 备份在 `cache/trash/skill-evolution.20261001-2109/`（含 126 条 eval_history + 报告）。
> 本节保留作为决策记录——它解释了当时为何「修，不弃」。


### 拆 ref 的选题优先级

优先拆**已带隐含结构**的技能：题目本身分了 `Round 0–6`、内部已分 `A/B/C/D` 层、已分 `L1/L2/L3` 的，
拆 ref 只是把**本来就写好的层级显式化**，不是重新组织内容，风险最低。

两个必须在动手前讲清楚的约束：
- **标注了「逐字保留 / 不可妥协」的段落（如 HRR 容量数字、隐私红线）必须整段搬 + 逐字节校验**，不许顺手润色。
- **拆 ref ≠ 减负**：ref 不被自动加载但可按需加载，收益要用「每次加载省多少」衡量，不是「库里总字节少多少」。
  主文件 = 每次都用的；ref = 偶尔查的。
