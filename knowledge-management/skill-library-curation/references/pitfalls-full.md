# pitfalls-full — 原 skill-library-curation/SKILL.md 第 322–391 行（逐字）

> 2026-09-26 「技能管理簇」5→1 合并：本节从主 SKILL.md 拆出，内容逐字未改。

## Pitfalls
- **The "skill count > ~50" trigger is already dead here.** At 219 skills any absolute count is noise. Rank by **share of the loaded prompt** (bytes of injected descriptions ÷ context budget) instead — that is what actually costs the user.
- **Name-prefix clustering misses the real duplicates.** Grouping by name stem finds same-family skills, but exact duplicates can sit in unrelated directories (`hermes-session-cleanup/` vs `hermes/hermes-session-cleanup/`). Always hash content, don't rely on names.
- **Deleting a dojo stub is safe; deleting all dojo output is not.** Distinguish by body: 37-line pure templates (one `## Context` line + generic advice) are worthless; longer dojo files with concrete commands may be worth folding into the overlapping hand-written skill instead.
- **A whole imported framework directory can be mis-fitted.** Bulk-bundled business/marketing or GPU-ML skill sets score ~0 on irreplaceability for this user. Archive the directory as a unit rather than reviewing 18 files individually.
- **LLM output wraps markdown in code fences.** When generating or improving markdown via LLM, strip leading/trailing ` ``` ` fences before writing. Check both cases: opening-only and opening+closing. In a batch of ~6000 files, ~6.5% had this issue.
- **Token budget exhaustion.** Calculate estimated consumption before launching LLM batch operations: ~5k-8k tokens/file. If estimated total >> available balance, switch to slim mode (target only deficient files). Have a fallback script ready.
- **Empty shell skills waste context.** Every skill loaded into context costs tokens. Deleting empty shells reduces context load.
- **Superset check is mandatory.** Never merge A into B without confirming B covers A's functionality. Reading only descriptions is insufficient — read full SKILL.md bodies.
- **Same topic ≠ same content.** Two skills covering one subject routinely share almost no text — measured `difflib` ratios of 2–13% between pairs whose *topics* were identical. Topic overlap justifies consolidating; it does not mean one can be deleted. Size the work as a content union before promising a deadline, and never tell the user a cluster is "trivial duplicates" on the strength of matching descriptions.
- **Description similarity is not evidence either.** Near-identical descriptions ("Add a provider + aliases + fallback" vs "接入 provider/别名/fallback") usually mean the same author wrote both at the same time — check whether the curator's ledger created them in the same session before treating a pair as independent.
- **The 30-day auto-archive eats rarely-triggered-but-important skills.** `archive_after_days: 30` silently drops any stale skill — and a guard that only fires on special occasions (a privacy-egress guard, a failover runbook, an MCP setup) is *supposed* to sit idle for months. Auto-archive has no notion of importance, so the loss is silent: no error, no notice, the skill is simply absent from the prompt when its trigger finally arrives. Sweep the 20–30-day band before archiving anything and protect those with `hermes curator pin <name>` (or raise `archive_after_days`). Archiving is recoverable via `hermes curator restore`; being *absent at trigger time* is not.
- **Utilisation is rarely the real problem — split usage is.** Measured on a 126-skill library: only 10 skills had `use_count == 0` (8%, three of them created that same day), while the top topic-duplicates were *both* heavily used (the multi-model review cluster: 116 + 52 = 168 uses for one job, two skills since merged into `multi-model-review`; likewise provider-config 34 + model-providers 19, cron-ops 29 + cron-notify 16). Rank merge candidates by the cluster's **summed** `use_count` — that is where utilisation is actually lost, because the agent must guess which of the pair to load. Report the usage distribution before proposing "delete the dead skills"; the honest answer is often "there are almost none".

- **A "missing" line is a hypothesis, not a loss.** The coverage check compares
  whitespace-stripped text, so a rewritten or translated line reports as missing.
  Strip **all** punctuation before comparing, not just whitespace: a hand-written
  Chinese integration uses `，（）；` where its source uses `,() ;`, and those
  variants alone accounted for ~20 of 88 reported misses. Frontmatter fields and
  bare section headings are not content either — exclude them up front.
  Classify every hit before reporting anything: pull the distinctive tokens
  (model IDs, config keys, command names) out of the source line and search the
  target for those. Raw counts of missing lines have come back as 6 and as 47 and
  both resolved to zero on item-by-item review — reporting the number first
  means retracting it later.
- **Byte conservation is the cheap cross-check.** A union merge's total bytes
  should not sit materially below the sum of its sources. A shortfall is
  physical evidence of dropped content that the line-coverage check can miss,
  because a source section that was dropped *whole* leaves no dangling line to
  match. Run it before accepting "all sections covered".
- **Do not integrate the content into SKILL.md *and* keep the source verbatim as
  a references/ file.** That stores the same text twice (a 4-skill merge measured
  39.5KB against 26.6KB of sources, +48%). Either integrate into SKILL.md and
  leave the verbatim originals in `.archive/`, or keep SKILL.md lean and put the
  full text in references/ — pick one. Moving a source's own `references/`
  subdirectory into the target is a separate requirement and still applies.
  To delete such a duplicate safely, diff the reference against SKILL.md first and
  inline whatever is unique. Frontmatter fields, bare section headings, and
  punctuation/backtick variants are NOT content — but a table of device IPs,
  accounts, or dated facts that only ever lived in the reference is, and losing it
  is silent. Delete only after the unique-line diff comes back empty.
- **A dropped-content merge is cheaper to repair than to redo.** Serialise the
  gaps into a list (source skill, section, verbatim line), hand the *backup* as
  the authority, and forbid structural change: "fill only these gaps, do not
  rewrite, do not delete." Measured 88 missing lines → 0 with the existing
  structure intact, for a fraction of the cost of re-merging.
- **Count skills with the generator's own command.** `find -L` (what
  `skill-catalog/register.sh` uses) follows symlinked skills; `os.walk` does not,
  and `find -maxdepth N` misses deeper paths. Mixing methods across a
  before/after comparison produces a phantom count change and blames the
  executor for damage that never happened.
- **A rule inside a skill is not automatically the user's rule.** Skills here are
  routinely curator-authored, and an AI-written mandate is formatted exactly like a
  user mandate. Check provenance before spending money or halting work on one: the
  ledger (`{"actor": "curator", "action": "create"}`) shows who authored the file,
  and rules that really came from the user carry the citation inline
  (`（2026-09-15 用户零容忍）`). A rule naming specific models, with no citation, is
  the author's implementation choice — surface it to the user rather than obeying it.
  Read hard gates for their failure mode too: "if the second opinion is unavailable
  (402/429), STOP" turns a routine provider rate-limit into a stalled task.
- **The curator rewrites skills mid-session.** A file read early in a task can change
  under you — one measured 11019B → 19694B inside a single session, with the ledger
  entry citing the *live* session id. Re-read (or hash) a skill before quoting it as
  the reason for an action, and never diff against a copy read minutes earlier.
  The same applies to any BRIEF that describes a skill's **current** contents: re-read
  the file first. An executor handed a BRIEF that contradicts what is on disk will
  **stop and ask** rather than force the edit — correct behaviour, since forcing it
  would clobber the concurrent change. Answer its question and re-dispatch; do not
  re-send the same BRIEF.
