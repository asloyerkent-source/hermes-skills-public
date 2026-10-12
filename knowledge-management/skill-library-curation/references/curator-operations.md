# Curator operations reference

Operator detail for Hermes' skill curator (`agent/curator.py`). The always-on
rules live in SKILL.md; this file is the command surface and the numbers.

## What it does

`maybe_run_curator()` forks an auxiliary AIAgent that may pin, archive,
consolidate or patch skills via `skill_manage`. It therefore mutates the library
with no user present. Bundled and hub-installed skills are never touched, and
auto-deletion never happens — archives stay restorable.

Two independent halves:

- **Deterministic prune** — always runs while the curator is enabled. Purely
  time-based: mark stale, then archive.
- **LLM consolidation fork** — opt-in, off by default. This is the half that
  builds umbrella skills.

## Command surface

| Command | Use |
|---|---|
| `hermes curator status` | enabled?, interval, stale/archive thresholds, consolidate on/off, managed vs unmanaged counts |
| `hermes curator usage` | per-skill use/view/patch counts + last activity + provenance (agent/bundled/hub) |
| `hermes curator run` | trigger a review now |
| `hermes curator run --dry-run --consolidate` | report what a merge pass would do |
| `hermes curator pin <skill>` / `unpin` | exempt a skill from auto-transitions and rewrites |
| `hermes curator backup` | tar.gz snapshot of the whole tree |
| `hermes curator rollback` | restore the tree, or one mutation by ledger id |
| `hermes curator ledger` | audit trail of every mutation |
| `hermes curator prune` | bulk-archive curator-managed skills idle ≥ N days |
| `hermes curator archive <skill>` / `restore <skill>` / `list-archived` | manual archive lifecycle |
| `hermes curator list-unmanaged` / `adopt <skill>` | skills with no provenance marker; adopting hands them to the curator |

## Configuration keys

Top-level `curator:` block in `config.yaml` (NOT under `auxiliary:`).

| Key | Default | Effect |
|---|---|---|
| `enabled` | `True` | master switch |
| `interval_hours` | 168 (7d) | how often a review is attempted |
| `min_idle_hours` | 2 | idle time before the poll will run |
| `stale_after_days` | 14 | unused N days → marked stale |
| `archive_after_days` | 30 | unused N days → archived out of the prompt |
| `consolidate` | `False` | the LLM umbrella-building pass |

Set with `hermes config set curator.<key> <value>` — it preserves comments.

## Two distinct "managed" populations

`hermes curator status` splits the library:

- **curator-managed** (`agent-created`) — subject to stale/archive transitions.
- **unmanaged** (`foreground-created`) — no provenance marker; the curator
  never auto-stales or archives these. `hermes curator adopt <name>` opts one in.

A skill written by a delegated agent in a foreground session lands in the
second bucket, which is why it can sit unused forever without being touched.

## The ledger

`~/.hermes/skills/.curator_ledger.jsonl` — one JSON object per mutation:
`{id, ts, actor, action, skill, evidence.session_id, before[], after[]}`.
`before`/`after` carry path + sha256, so a recorded change can be diffed against
the live file instead of trusted. Actions seen: `create`, `patch`, `write_file`,
`remove_file`, `archive`.

Use it to answer two questions:

- **Who wrote this skill?** `actor=curator` means the library created it, not a
  person.
- **Was this file changed by that run?** Compare the `after` sha256 to the
  current file hash.

## Gating the curator: risk-tiered approval instead of an on/off switch

The curator writes the library with no user present. Turning it off is the
wrong fix — self-learning is worth keeping. Gate it by risk.

**Before building anything, check what already exists.** Hermes ships the two
mechanisms a gate needs; a `no_agent` cron watching the ledger needs no core
changes:

| Need | Existing mechanism |
|---|---|
| see what was written | `hermes curator ledger` / `.curator_ledger.jsonl` |
| undo exactly one edit | `hermes curator rollback <entry_id>` (`skill_ledger.rollback_entry`) |
| record it happened | `skill_ledger.record_mutation` (already fires on every write) |

**Tier by the ledger's own action distribution**, not by intuition — measure
`action` counts first:

- **Low risk, auto-pass** — `patch` / `write_file` / `create`: adds experience
  to a skill. Reversible by `rollback_entry`, so a bad write costs one command.
- **High risk, ask the user** — `delete` / `remove_file` / `archive`:
  irreversible routing damage; one wrong call breaks skill resolution.

The gate is a small script (cursor file + `no_agent` cron, silent when clean,
like any other watchdog). Full-or-nothing is the wrong shape: requiring approval
for all 900+ low-risk patches stops the curator dead, which is why "just add an
approval prompt" fails.

**Do not auto-rollback high-risk entries.** A delete needs a human decision, and
rolling back while the tool is mid-run can trip over its own locks. Report and
wait.

⚠️ **The ledger is one JSON object per line — never grep it with anchored
regexes.** `grep -E '^(archive)$'` matches nothing (each line is a whole
object), so the gate silently never fires while still exiting 0. Parse the
field with `python3 -c 'import sys,json; ...'` instead.

## Reconciling the curator against the criteria-fingerprint check

`skill_repo_doctor.py`'s 8th check fingerprints its own criteria files and
reports "someone edited my own judgement". The curator legitimately edits those
same files, so **every self-learning pass trips the alarm and the baseline never
catches up** — it fires again on the next pass.

Do not exempt the check wholesale (that is silently disarming it) and do not
disable the curator. **Reconcile against the ledger**: when a fingerprint
mismatches, look up that file's `after` sha256 in the ledger; if it matches, the
write is accounted-for self-learning → pass silently and renew the baseline. If
it doesn't match, still report.

The general rule: **when a checker and a legitimate writer fight over the same
files, connect them through the writer's audit trail** — never pick a side.
Requires the writer to log full content hashes; without that, keep reporting.

## Debugging trap: hand-running a fix does not reset `failure_streak`

`failure_streak` / `last_status` are written by the **scheduler**, not by your
script. Fixing the script and running it by hand leaves both stale, so the job
still looks broken until its next scheduled fire.

- Don't report debug-period streak counts as real failure counts.
- To confirm what the scheduler last saw: `SELECT status,started_at FROM
  executions ORDER BY rowid DESC LIMIT 6` and check whether the newest run is
  before or after your fix.

## Cost and scale

The consolidation fork must read the whole library to judge overlap.

- Input floor: `find ~/.hermes/skills -name '*.md' | wc -c`
- Real cost is several times the floor (reading once is not how it runs).
- Runs on whatever `auxiliary.curator` is pinned to. A free-tier model with a
  few hundred files will not finish inside a normal command timeout — it gets
  killed and writes no report, which looks like a failure but is scale.

Before enabling it, decide explicitly whether the recurring spend beats doing
reviewed merges by hand when the library actually needs them.
