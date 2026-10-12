# when-to-use-and-procedure — 原 skill-library-curation/SKILL.md 第 6–26 行（逐字）

> 2026-09-26 「技能管理簇」5→1 合并：本节从主 SKILL.md 拆出，内容逐字未改。

# Skill Library Curation

## When to use
User asks to review, consolidate, optimize, or audit the skill library. Also triggers when skill count exceeds ~50 (check via `ls ~/.hermes/skills/ | wc -l`).

## Procedure

### Evidence sources (use these instead of guessing "is it used?")

Frequency/irreplaceability judgements must be grounded in machine evidence, not impressions:

| Source | Path | What it proves |
|--------|------|----------------|
| Usage telemetry | `~/.hermes/skills/.usage.json` — render with `hermes curator usage` | **Authoritative usage counts.** Per skill: `use_count`, `view_count`, `last_used_at`, `state` (active/stale), `pinned`, `created_by`. Prefer this over patch counts — a patch means "used *and* found lacking", not "used". |
| Curator ledger | `~/.hermes/skills/.curator_ledger.jsonl` | Patch-count proxy. A skill only gets patched because it got used and found lacking. Count `{"skill": ...}` occurrences — the distribution is extremely long-tailed (top skill 49 edits, most skills 0). |
| Loaded-skill manifest | `~/.hermes/.skills_prompt_snapshot.json` | Which skills the runtime actually loads, plus per-skill mtime/size in `manifest`. |
| Bundled manifest | `~/.hermes/skills/.bundled_manifest` | Which skills shipped with the bundle (upstream) vs were authored for this machine. Upstream ≠ unused, but score irreplaceability lower. |
| Content hash | `sha256sum` each SKILL.md | Exact-duplicate detection. Identical content under two paths is invisible to name-prefix scanning. |

Ownership signal: `metadata.hermes.generated_by: hermes-dojo` in frontmatter, or body text `created by Hermes Dojo after analyzing session logs`, marks auto-generated output. **Check the body before deleting on this signal** — some dojo output carries real content; only the 37-line templates are worthless.
