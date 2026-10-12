# skills-tree-management — 原技能正文（逐字）

> 2026-09-26 「技能管理簇」5→1 合并：本文件逐字并入源技能 `hermes-skills-management` 的 SKILL.md 正文（去 frontmatter）。
> 源目录 `devops/hermes-skills-management/` 已归档于 `.archive/hermes-skills-management/`，原件逐字保留。

# Hermes Skills Management

## Skill Discovery

Hermes discovers skills via `agent/skill_utils.py::iter_skill_index_files()`:
- Recursive `os.walk` from `~/.hermes/skills/`
- Finds any `SKILL.md` at any depth
- Supports `skills/<category>/<skill>/SKILL.md` layout
- Follows symlinks (`followlinks=True`)

**Implication:** Moving skills into subdirectories (e.g., `flows/`, `connectors/`) works without code changes.

## Directory Reorganization

### Safe Move Checklist

1. **Backup first:** `cp -r ~/.hermes/skills ~/.hermes/skills.backup-<timestamp>`
2. **Create subdirs:** `mkdir -p skills/flows skills/connectors`
3. **Move skills:** `mv skills/<name> skills/flows/<name>`
4. **Fix symlinks:** Relative symlinks are depth-sensitive
5. **Fix path resolution:** Scripts using `dirname $0` need recalculation
6. **Regenerate INDEX:** `bash skills/knowledge-management/skill-library-curation/scripts/register.sh`
7. **Verify:** `hermes skills list` + `skill_view <name>`

### Symlink Depth Pitfall

Relative symlinks break when their parent directory moves deeper:

```
# Before: skills/json-canvas -> ../../.agents/skills/json-canvas
# After moving to skills/flows/json-canvas:
#   needs ../../../.agents/skills/json-canvas
```

**Fix:** After moving, run `find -xtype l skills/` to find broken symlinks, then recalculate depth.

### Path Resolution in Scripts

Scripts that locate their own directory via `dirname $0` break when moved. **There is no
universal `../..`** — the level count depends on where the script sits, and a merge changes it:

| script location | levels to `skills/` | expression |
|---|---|---|
| `skills/<skill>/scripts/<file>` | 2 | `../..` |
| `skills/<cat>/<skill>/scripts/<file>` | 3 | `../../..` |
| `skills/<cat>/<skill>/scripts/<sub>/<file>` | 4 | `../../../..` |

A wrong count does **not** error — it silently resolves one level too shallow and writes the
output into the wrong directory while reporting success. Real case: `register.sh` moved from
`skills/flows/skill-catalog/` (2 levels) to `skills/knowledge-management/skill-library-curation/scripts/`
(3 levels); it kept `../..`, resolved to `skills/knowledge-management/`, and generated a stray
`INDEX.md` there.

**Fix and verify:** count the levels from the script's own directory up to `skills/`, update the
expression, then **run the script and read the target path it prints** — `bash -n` only checks
syntax and passes on a wrong path. Delete anything the bad run produced.

Scripts that climb all the way to `~/.hermes/` (hook installers, workspace-relative helpers) need
the same count measured against `~/.hermes` instead of `skills/` — that is one level *more* than
the table above, and it is verified the same way: run it, read the resolved path it prints.

In Python, `Path(__file__).resolve().parents[N]` is the same arithmetic — pick N by the same
count, never by habit.

## skill-catalog Generator Pitfalls

The `register.sh` script (in `skills/knowledge-management/skill-library-curation/scripts/`) has several failure modes:

### Multibyte Truncation
```bash
# BREAKS: cut -c truncates by byte, splitting CJK/emoji
short_desc=$(echo "$desc" | cut -c1-60)

# FIXED: bash substring is character-wise
short_desc="${desc:0:60}"
```

### CRLF in Frontmatter
Skills with Windows line endings (`\r\n`) get names with trailing `\r`, breaking name matching.

```bash
# FIXED: strip \r from parsed values
name=$(grep -oP 'name:\s*\K.*' "$sk_file" | head -1 | tr -d '\r')
```

### Symlink Exclusion
`find -type f` skips symlinks, so symlinked skills are missing from INDEX.md.

```bash
# FIXED: use -L to follow symlinks
find -L "$SKILLS_DIR" -name "SKILL.md" -type f
```

### Self-Path Derivation
Hardcoded `skills/skill-index/register.sh` breaks when the script moves.

```bash
# FIXED: derive from $0 location
SELF_REL=$(realpath --relative-to "$WORKSPACE_DIR" "$(realpath "$0")")
```

## Classification Scheme

Current `skills/` layout:

```
skills/
├── flows/              # Process knowledge, thinking frameworks, analysis
│   ├── property-analysis/
│   ├── thinking-frameworks/
│   └── ...
├── connectors/         # External system/device integration
│   ├── web/
│   ├── codebase-memory/
│   └── ...
├── productivity/       # User productivity tools
├── automation/         # Cron, scheduling
├── devops/             # Infrastructure
└── ...                 # Other categories
```

**flows/** = pure Markdown, no external dependencies, describes how to think/work
**connectors/** = integrates with external tools, APIs, devices; may declare permissions

## The curator owns the lifecycle — read its state before merging anything

Hermes ships a skill curator (`agent/curator.py`) that runs on a schedule and
also forks mid-session. It **creates, patches, stales and archives skills by
itself** (`actor=curator` in the ledger). Duplicate clusters are usually its
output, not the user's: it appends a skill per session topic and, by default,
never merges.

**`consolidate` is OFF by default** (`DEFAULT_CONSOLIDATE = False`) — it prunes
on a timer but builds no umbrellas. That is the root cause of a library that
grows sideways. Check the live state; never infer it:

```bash
hermes curator status     # enabled? interval, stale/archive thresholds, consolidate on/off
hermes curator usage      # per-skill use/view/patch counts + last activity, with provenance
```

**Utilization is measured, not guessed.** `~/.hermes/skills/.usage.json` is the
source of truth (`use_count`, `view_count`, `last_used_at`, `state`, `pinned`,
`patch_count`). Count before proposing deletions:

- `use_count == 0` is usually RARE. A healthy library is mostly used, and a
  brand-new skill legitimately has zero. Do not report "a pile of dead skills"
  without the number.
- The real defect is usually **split usage**: two skills covering one job both
  rank high (`use=116` and `use=52` for the same task) because the agent has to
  guess which to load. Rank merge candidates by **combined** use count, not by
  size or intuition.
- `use=0` alone is not grounds for pruning; the curator itself refuses the case
  below 30 days for exactly this reason.

**Auto-archive is the silent-failure risk, not clutter.** Anything unused for
`archive_after_days` (default 30) leaves the prompt with no error and no notice.
Rarely-triggered-but-critical skills — privacy guards, failover runbooks,
per-machine setup — look identical to dead ones under a pure recency rule.

1. Sort `.usage.json` by `last_used_at` to see what is near the line.
2. `hermes curator pin <name>` the ones whose *trigger* is rare by nature.
   Pinning also blocks automated rewrites, so pin deliberately.
3. Raise the threshold rather than relying on pins alone:
   `hermes config set curator.archive_after_days 90`.

**Do not read causation from timestamps.** A foreground `--dry-run` and the
background curator can both write patches inside the same window, both logged
`actor=curator`. Attribute a change by its `evidence.session_id` (a cron job's
session id looks like `cron_<id>_<ts>`), and confirm a run actually wrote a
report before blaming it.

### Config edits go through `hermes config set`

`hermes config set <dotted.key> <value>` rewrites the YAML **with comments and
ordering intact**. This is the supported path and removes the hand-edit risk
entirely — verify it held:

```bash
grep -c "^\s*#" ~/.hermes/config.yaml          # before
hermes config set curator.archive_after_days 90
grep -c "^\s*#" ~/.hermes/config.yaml          # after — must match
python3 -c "import yaml;yaml.safe_load(open('$HOME/.hermes/config.yaml'))"
```

Never rewrite `config.yaml` with a YAML library (it strips comments), and never
hand-edit a key that `hermes config set` can reach. The curator's own settings
live in a **top-level** `curator:` block — not `auxiliary.curator`, which only
pins the model the curator calls.

### Enabling consolidation is a cost decision, not a cleanup

The consolidation pass reads the **whole** library before it can judge overlap.
Measure before enabling — `find ~/.hermes/skills -name '*.md' | wc -c` sets the
input floor, and thinking plus output multiply it several-fold, every
`interval_hours`.

`hermes curator run --dry-run --consolidate` reports what it *would* do, but it
is bounded by your own timeout. On a large library it can be killed before it
writes any report, which reads as failure and is really just scale. When it does
not finish, merge deliberately instead: a reviewed, briefed, independently
verified merge beats an unbounded pass, and costs nothing while idle.

## Merging Overlapping Skills

Sibling skills covering one topic must be collapsed to one, not left as a
redundant cluster. A SKILL.md is a **dispatch table**: five skills whose
descriptions all say "write code via an agent" make every one of them match,
so none is reliably loaded.

**Shape after merge:** one SKILL.md holds the always-on workflow (decision
tree, ironclad rules, selection table); the depth moves to `references/`
named by topic. Source skills get archived, not deleted:
`mv <src> .archive/<src>-merged-into-<dst>` so it stays reversible.

### Never trust a subagent's "references updated" claim

Agents report the merge complete after updating only what they happened to
open. A merge that moved 5 skills left all 5 rows in `INDEX.md` still
pointing at the now-archived paths — the worst kind of dangling reference,
because the index is where people start looking.

**Recount the hits yourself, never trust the report:**

```bash
grep -rnE '<src1>|<src2>' ~/.hermes/skills --include='*.md' \
  | grep -v '/.archive/' | grep -v '/.hub/'
```

Then classify each surviving mention — only the second kind should change:

| Kind | Example | Action |
|---|---|---|
| Historical provenance | `> 来源：合并自 xxx` | keep (archaeology) |
| Live pointer | `path/to/SKILL.md` in a table row | **must update** |
| Audit record | describing a past audit finding | keep, add one line noting the merge |

State "do not change X" explicitly in the task brief, or agents either
mass-rewrite history or skip everything.

**Baselines in the brief must be counted first** (`find … -name SKILL.md | wc -l`).
A stale target count makes the agent either think it failed or use the
discrepancy to excuse what it skipped.

### Prove the union is lossless before accepting the merge

Two skills on one topic are usually **complementary** (one is implementation,
one is process), so the merge is a union, not a pick-one. Write "union — do not
drop content because it looks redundant" into the brief, then verify
mechanically instead of by reading:

1. Split each source into sections (`^#{1,3} ` headings with non-empty bodies).
2. Normalize whitespace, then check each source body's opening characters appear
   somewhere in the merged SKILL.md **or any of its references**.
3. Require `unmatched = 0` and print that count.

Aggregate size is the cheap smell test: merged SKILL.md + references should be
at least as large as the sum of the sources. A merge that shrinks the library
has dropped content.

### Keep the merged SKILL.md lean; push depth to references

A body over ~24k characters is itself a consolidation target — the whole
SKILL.md loads on every `skill_view`, so folding four skills into one giant file
recreates the problem in a new shape. Target: SKILL.md carries the routing
table, the ironclad rules and the pitfalls index; per-topic depth becomes
`references/<topic>.md`. Collapse dated variants of one reference (three
`*-quirks-<date>.md`) into a single `*-quirks.md` with dated sections.

### Renaming a skill breaks its inbound references

After archiving a source, these still point at the dead name:

- **cron jobs** — a job whose `skills` or `prompt` names the old skill stops
  resolving. Rebind through the CLI, never by editing `jobs.json`:
  `hermes cron edit <job_id> --skill <new-name>`
- `INDEX.md` rows and other skills' "see also" lines.
- Scheduled-task prose that names the skill without binding it.

Grep the tree for the old name, then **exclude history** or you will "fix"
records that must stay: `.archive/`, `*.bak*`, `.usage.json`,
`.curator_ledger.jsonl`, `model-logging/logs/`.

### Keep backups out of the skills tree

`cp -r <skill> <skill>.bak-<ts>` inside `skills/` leaves a second `SKILL.md`
that the discovery walk finds, so every duplicate scan reports it. Back up to
`~/.hermes/skill-backups/<batch>-<ts>/`, and use `hermes curator backup` for a
whole-tree snapshot (it also runs automatically before a real curator run).

### Credentials travel with the content

Archived skills often hold secrets inline (app tokens, API keys). Moving a
`references/` file copies the secret too. Mask it, move it to `.env`, or park
it in a clearly-labelled pending-migration file before archiving.

**A redaction brief that excludes directories creates blind spots.** Scoping a
secret scan to "skip `.archive/` and `.hub/`" leaves every archived copy in
place — those exclusions exist for *skill loading*, not for *content hunting*,
and the two scopes are not the same. Enumerate copy sites first
(`grep -rln <marker> <root>`), then classify each as legitimate (`.env`),
system-managed (session DB, shell history, timestamped backups), or
redactable, and scope the brief to the whole set.

**Check the egress paths before recommending remediation.** Whether a secret
in a file matters depends entirely on whether it can leave the machine: look
at sync config (a Syncthing folder list may cover only the vault, not
`skills/`), mounted cloud drives, and `git remote` on any directory that
contains the file. A secret present only on the user's own machine with no
sync or push path is contained — say so plainly and price the fix honestly
(redacting copies is containment; rotating is the only real fix and is rarely
worth the downtime when nothing has left). Do not alarm on the raw grep count.

### frontmatter after a rewrite

`metadata.hermes.related_skills` (and any `merged_from`) survive a rewrite
with stale names in them. Parse with `yaml.safe_load`, then check each entry
with `os.path.exists`; drop anything resolving into `.archive/`.

## Writing skill files is coding, not prose

Editing a SKILL.md or `references/` file is **writing executable process
code** — it dictates how every future session acts, exactly like a `.py`.
It never qualifies as "just writing markdown".

Correct split: the agent designs the structure and writes the brief → a
delegated agent (Codex/Pi) authors the files → verify. Doing it with
`skill_manage` one file at a time means breaking the rule inside the very
skill that states the rule.

**One agent per batch.** Before dispatching, confirm no earlier agent is
still running (`pgrep -af "codex exec"`) — two agents editing one directory
overwrite each other.

**Absolute paths everywhere.** A shell session whose cwd was deleted makes
`cd ~/.hermes/skills` fail with exit 126; pass the terminal's `workdir`
parameter instead of trying to `cd` back.

## Verification

Operator detail for the curator — command surface, config keys, ledger format,
managed-vs-unmanaged split, cost scale — is in
`references/curator-operations.md`.

After any reorganization:

```bash
# 1. Check for broken symlinks
find -xtype l skills/

# 2. Verify Hermes discovers all skills
hermes skills list | grep -c "enabled"

# 3. Test load a sample from each category
skill_view <flow-skill>
skill_view <connector-skill>

# 4. Regenerate INDEX
bash skills/knowledge-management/skill-library-curation/scripts/register.sh

# 5. Validate INDEX
python3 -c "assert open('skills/INDEX.md','rb').read().decode('utf-8')"
```
