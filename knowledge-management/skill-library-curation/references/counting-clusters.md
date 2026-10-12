# counting-clusters — 原 skill-library-curation/SKILL.md 第 167–315 行（逐字）

> 2026-09-26 「技能管理簇」5→1 合并：本节从主 SKILL.md 拆出，内容逐字未改。

## Answering "how many clusters are left"

A merge campaign spans many sessions, so the pending-cluster queue lives **only in
chat history** — there is no plan file on disk. Answer from the session store plus the
live tree; never from memory.

1. **Recover the queue.** The plan table was written as a chat message, and
   `~/.hermes/sessions/` holds only request dumps, so query the session store:
   ```bash
   sqlite3 ~/.hermes/state.db "select id,role,substr(content,1,2000) from messages \
     where content like '%个簇%' and id < <latest_msg_id> order by id desc limit 15"
   ```
   无 `sqlite3` CLI 时用 `python3` 的 `sqlite3` 模块读同一个库，别为了跑一条查询去装包。
   Take the **newest** queue table for the campaign. Older copies still list clusters
   merged since, and a context-compaction summary will re-serve those stale ones
   verbatim as if current.
2. **Count the deliverable, not the plan.** Enumerate live skills (a directory holding
   `SKILL.md`, skipping `.archive/`, `*.bak*`, `skill-backups/`, `.curator_backups/`)
   and check that each planned cluster's members are **still present separately**. A
   cluster is pending only while ≥2 members remain loaded; once they collapse to one,
   the cluster is done regardless of what the plan says.
   **插件根的技能不算成员**：形如 `~/.hermes/hermes-relay/skills/` 的目录由插件投递，
   不归用户技能库管——合并进用户技能树会在插件下次更新时被覆盖，或被判成重复。
   它们既不该进簇，`find` 数活动树时不出现也不是计数 bug（两个口径的差值要先看是不是这类路径）。
   **两个计数口径都是对的，别去"修"那个差值。** `scripts/register.sh` 用 `find -L`
   （跟随软链，把 `~/.agents/skills/` 下的软链技能也算进来），而 `scripts/skill_product_audit.py`
   数真实目录、不跟软链——实测同一时刻 INDEX 报 78 条、体检报 `skills=74`，差的正是
   4 个软链（`connectors/obsidian-cli`、`flows/json-canvas`、`obsidian-bases`、`obsidian-markdown`）。
   报告数字时**说清用的是哪个口径**；怀疑计数异常时，先 `ls -la` 看那些路径是不是软链，
   两个数字都解释得通就不是 bug。
3. **Report the number with its basis:** the live skill count, that each cluster's
   members were re-checked individually, and a timestamp. A bare count recalled from
   memory is not an answer this user accepts.

## 先分诊：这个簇到底还剩什么活

**成员还在活动树 ≠ 内容还没合并。** 这两种半成品的工作量差一个数量级，排期前必须先分清：

1. **内容已搬、源未归档**（实测最常见）。早期一轮审计会把源 SKILL.md **逐字复制**进目标的
   `references/<源名>.md`，然后忘了归档源目录——于是队列里永远显示「还有 N 个成员」。
   判据：目标技能里存在同名 ref，且与源 SKILL.md 逐行 diff 只差那几行「合并来源」表头。
   → 剩余工作 = **归档源 + 结构 pass + 修活指针**，不需要再读一遍源正文重新整合。
2. **真·未吸收**。目标里找不到对应 ref，diff 大面积未命中。→ 才走完整 union merge。

用本技能的探针跑，别手写 diff：

```bash
python3 ~/.hermes/skills/knowledge-management/skill-library-curation/scripts/ref_absorption_check.py \
  <源技能目录> <目标技能/references/那个ref.md>
```

**一个簇里两种形态可以并存**：同一簇 3 个源，2 个早已被逐字吸收、1 个从没动过，是常态。
**逐源分诊，别整簇套一个方案。** 反向也成立：源还在活动树，不能据此断定簇没做。
另外要看源目录里有没有**没被搬过来的子文件**（源技能自带的 references 子目录、templates、scripts）——正文搬了、
附件没搬是高频漏项，逐源走一遍文件清单而不是只看 References 段。

Pitfall: **a cluster marked "skipped" is not inert.** Skipping means "do not do this
now", not "nothing happened here" — if a partial merge already ran inside it, the
artifacts stay live: concatenated targets, plus source members whose content already
sits inside the target but which were never collapsed. Re-check a skipped cluster with
the same live-member count as any other. Observed: a cluster recorded as skipped in the
newest queue table was holding two skills at 9.9× and 3.0× the size ceiling, plus a
third member still separate whose content also sat in the target's references (only
0.8% line overlap — so it was neither safely deletable nor actually merged).

Pitfall: **a deliberately-kept member needs its reason written into the target's
SKILL.md**, otherwise every future count re-flags the cluster as unfinished. One
member of a 7-source cluster was kept on purpose (a third-party git project, not a
skill); with that reason living only in chat history, the cluster reads as "2 members
alive" forever and looks like pending work.

Pitfall: an audit document's `合并→<target>` rows go stale in **both** directions. A
source still present means pending; but a row is also dead weight when its **target**
has since been merged into a third skill or renamed — verify the target exists in the
live tree too, or you count orphaned sources as work that has nowhere to go.

## 1. Enumerate
```bash
cd ~/.hermes/skills && for skill in */; do
  name=$(basename "$skill")
  lines=$(wc -l < "$skill/SKILL.md" 2>/dev/null || echo 0)
  desc=$(grep -m1 "^description:" "$skill/SKILL.md" 2>/dev/null | sed 's/^description: *//')
  echo "$name|$lines|$desc"
done
```

### 2. Classify by function
Group skills into functional domains. Use control theory as an organizing lens:
- **Feedback control**: skills that provide immediate correction/audit/status
- **Black box analysis**: skills that analyze without opening the system
- **Information flow**: skills for data extraction/transformation/filtering
- **Stability**: skills for system health, rollback, error recovery
- **Optimal control**: skills for cost/performance optimization
- **System modeling**: skills for abstraction, graph queries, simulation
- **Human-machine**: skills for UI, voice, judgment distillation

### 3. Identify candidates

**Empty shells** (safe to delete):
- < 10 lines of actual content
- Just a description + forward to another skill
- No unique rules or procedures

**Redundant pairs** (A ⊂ B, merge A into B):
- B's SKILL.md covers everything A covers
- A has no unique references/ or scripts/ not in B
- Merge: move A's unique content into B, delete A

**Complementary pairs** (A + B → one skill):
- Same domain, different aspects
- Neither is a superset, but together they form a coherent whole
- Merge: create new combined skill, delete both

### 4. Verify before merge
For each proposed merge:
- Read both SKILL.md files fully
- Check references/ and scripts/ subdirectories
- Confirm no unique functionality is lost
- Confirm the merged skill stays under 15KB (skill-evolution size limit)

> ⚠️ **2026-10-01 已归档**：依赖 `gepa`/`fastembed` 缺失、无 cron 任务、126 次评估 0 采纳。
> 备份在 `cache/trash/skill-evolution.20261001-2109/`（含 126 条 eval_history + 报告）。
> 本节保留作为决策记录——它解释了当时为何「修，不弃」。


**Pick the executor by task shape, not by price.** A union merge (keep
everything from N skills in one) is an *absence-detection* problem, not a writing
problem — the difficulty is noticing what did NOT come out the other side.
Weak/free models hold the structure together and quietly drop the specifics:
the exact model IDs, config keys, script invocations, dated iron rules. Those
specifics are the whole reason the skill existed. Route union merges to the
strongest model available and to a cheap one only for steps with a single
correct answer, and only with a verification pass behind it.

### 5. Model choice for structural changes

Merges are **content-critical**: the risk is not wrong structure but silently dropped
specifics (model IDs, config keys, dated iron rules). Two rules:

- **Worker** — route union merges to the **strongest model available**. A cheap model is
  fine only for steps with a single correct answer, and only with a verification pass
  behind it. (Measured: a cheap model kept the structure right and dropped 88 lines of real
  content; the rework cost more than the saving.)
- **Verifier** — verification must be **independent of the worker**: re-derive the result
  from the sources, do not read the worker's report. Line-level coverage (every informative
  source line looked up in the target) beats section counts, and total-byte conservation
  (merged total ≪ sum of sources) is the physical evidence that content was lost.

A second-model review is **optional, not a gate**. Use it when the merge is large or the
call is genuinely ambiguous. **Never block a merge on a provider being unavailable**
(402/429) — record the gap and proceed with independent verification, or hand verification
to a different model.

### 6. Execute
- Back up every source directory **outside** the active tree
  (`~/.hermes/skill-backups/<cluster>-<timestamp>/`). A backup placed under
  `skills/` is picked up by the duplicate scan and by the next audit as if it
  were live content.
- Use `skill_manage` with action=patch for merges into existing skills
- **Archive, never delete**: move absorbed skills to
  `.archive/<name>-merged-into-<target>/`. The archive is the rollback path and
  the only remaining copy of the verbatim original.
- Preserve references/ by moving them into the target skill's references/
- Update every external reference found in Gate B
- Regenerate the index with the generator, never by hand:
  `bash flows/skill-catalog/register.sh`
- Update memory with new skill count and merge summary
- **Dispatch the merge; do not perform it in the main context.** Reading N source
  SKILL.md files and integrating them verbatim costs tens of thousands of tokens of
  the *main* context — measured: one hand-run 4-skill merge took 40+ tool calls and
  a context compaction, after which some detail was unrecoverable. The same reading
  done inside a subagent's context costs the main model nothing. Main context is
  scarcer than money, so "cheaper to do it myself" is the wrong arithmetic.
- **Split a large merge into stages that each produce a verifiable artifact.** One
  session told to read + write + verify tens of KB aborts silently: two runs stopped
  at "step 1 (backup)" with the sources untouched and no output at all. Tell the
  executor to save as it goes instead of holding everything to the end, state which
  step the previous run reached so it does not redo work, and require it to report
  how far it got rather than claim completion.
- **After an abort, verify state before re-dispatching** — sources unmodified, no
  half-written target, backup intact — then resume from the recorded step.
- **A union merge has TWO deliverables — content and structure. Book them separately.**
  A strong executor nails content (zero loss) and silently skips structure: it concatenates
  the N source documents end to end, each keeping its own opening (`Trigger:` / `## Why`
  left dangling inside an otherwise translated document), with no trigger block, no
  navigation, no unified headings. Line coverage and byte conservation both pass, so
  **"verification green" does not mean the merge is finished** — an off-the-shelf report of
  "8/10 checks passed" commonly means structure passed and integration was never attempted.
  After the content pass, run an explicit **structure pass**: one-sentence purpose, trigger
  list, navigation table, numbered sections, one heading language. Keep exact commands,
  error strings, paths and model IDs **verbatim in their original language** — translating
  those is where precision is lost and where the coverage check starts reporting false
  misses. The structure pass reads only existing files, so it is a re-ordering job the main
  context can do cheaply; do not re-send the sources to the executor for it.
- **Read the executor's self-report by layer.** On union merges the *structural* claims
  (sources moved out of the active tree, archive populated, frontmatter parses, index
  regenerated, hard-coded paths fixed) verify true almost every time; judge the *content*
  claims yourself. Expect the executor to be right about what it did and wrong about how
  complete it was. When it reports an out-of-scope defect instead of silently fixing it,
  that is correct behaviour — the fix belongs to the caller.
