# Skill Audit Checklist

Run this before AND after any merge. Two mechanical tools back it:
`~/.hermes/scripts/skill_ref_lint.py` (pointer → file, i.e. broken links) and
`scripts/skill_product_audit.py` (file → pointer, i.e. orphans, plus SKILL.md size,
repeated blocks, stale self-references). Both must be RUN, not read — a tool whose
output nobody looked at is how a wrong conclusion reaches live config.

## Pre-Merge Verification

For each proposed merge (A into B), confirm:

### Functional Coverage
- [ ] B's SKILL.md covers all triggers in A's description
- [ ] B's procedure includes all steps from A
- [ ] B's pitfalls include all pitfalls from A
- [ ] A has no unique references/ files not present in B
- [ ] A has no unique scripts/ not present in B

### Size Constraints
- [ ] Merged SKILL.md ≤ 12KB (12288B — the ceiling the audit script enforces)
- [ ] Merged references/ directory is under 50 files
- [ ] No single reference file exceeds 10KB

### Trigger Preservation
- [ ] Merged skill's description includes all trigger words from both A and B
- [ ] No existing user workflows that reference A's name will break (update memory if needed)

### Independent Verification (not a second model)
- [ ] The result was re-derived from the sources by someone other than the writer
- [ ] Line-level coverage checked, with every reported "missing" line classified before it is reported
- [ ] Byte conservation checked (merged total not materially below the sum of sources)

A second-model review is **optional, never a gate**. Never block a merge on a provider
being unavailable (402/429) — record the gap and proceed with independent verification.

## Post-Merge Verification

- [ ] Re-read merged SKILL.md — is it coherent?
- [ ] Check for duplicate pitfalls or rules
- [ ] Verify all internal links (references/, scripts/) still resolve
- [ ] **Both directions checked**: pointer → file AND file → pointer. A reference file
      nobody links to is written-but-invisible, and the linter cannot see it.
- [ ] No orphan refs: every file under `references/` and `scripts/` is named somewhere in SKILL.md
- [ ] No stale self-references: after moving a section into a ref, grep SKILL.md for
      「见「」/「本文件」/「本技能内」 and repoint each; a ref that calls itself "the
      authoritative copy of SKILL.md §X" needs the same treatment
- [ ] Update memory with new skill count and merge summary
- [ ] If a skill was deleted, verify no other skill references it by name

## Reading orphans correctly

An orphan is not automatically original content:

- **An orphan whose basename equals another ACTIVE skill's name**
  (`~/.hermes/skills/hermes-ops/hermes-gateway-troubleshoot/references/hermes-telegram-repair.md` sitting inside the gateway skill) is a
  **copy of that skill**, not orphaned originals. It marks a merge that was started and
  abandoned: content was copied in, never linked, source never retired. Before deleting
  the copy, confirm the source still exists and still covers it — and diff the two,
  because the **source may have been updated after the copy was taken**, in which case
  the copy is stale rather than merely redundant. Deleting a stale copy is right;
  deleting the only copy of something is not.
- **An orphan whose name matches nothing else** is content written and never wired up.
  Link it from SKILL.md rather than deleting it — 13.4KB of one skill's reference set
  was invisible exactly this way.

A fake merge leaves traces on **both** sides: the source declares "merged into X"
while its body is intact, and X holds an unlinked copy. Sweep both; fixing only the
declarations leaves the duplicates in place.

A skill directory with `references/` and `scripts/` but **no SKILL.md** is not a skill
at all — it is never loaded, yet other skills may still point into it. Move its files
into the live skill that references them; do not treat it as a skill to merge.

## Red Flags (STOP if any present)

- A has unique scripts/ that cannot be moved to B without breaking paths
- A's references/ contain user-specific data (credentials, IPs) that shouldn't be in B
- B's SKILL.md is already near the 12KB ceiling (the merge pushes it over; plan the
  structure pass up front rather than discovering it in review)
- The merge would reduce trigger coverage (fewer ways to invoke the skill)
- A protection marker (`sacred` / `never merge`) or a pinned skill appears in the cluster

## Attributing size overage

Measure the whole library before blaming the merge pipeline. SKILL.md overage is a
library-wide condition, not a merge artifact: measured 24 of 106 skills over the 12KB
ceiling, and the worst offender (120KB, 9.8x) had **never been merged at all**. A
merge-scoped sample convicts the wrong cause. Run `skill_product_audit.py` with no
`--skill` first, then compare merged against never-merged groups before concluding
anything about the merge process.
