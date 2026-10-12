# 档案卫生：两区原则与工作流 — 原技能 `archive-hygiene` 正文（逐字）

> 2026-09-27 「文件整理簇」4→1 合并：本文件逐字并入源技能 `archive-hygiene/SKILL.md` 的正文（去 frontmatter）。
> 源目录已归档于 `.archive/archive-hygiene/`，原件逐字保留；备份 `~/.hermes/skill-backups/merge-cleanup-20260927-001231/`。

# Archive Hygiene (personal file-archive management)

## When to use
- User says they downloaded "many files" and needs them organized, deduped, or prevented from turning into a "垃圾场" (junk yard).
- User wants a recurring cleanup/review rhythm for a large archive.
- User mentions Obsidian / LLM-Wiki / AnythingLLM / knowledge base built from their files.
- User has a server/NAS (e.g. Linux box) acting as central storage alongside Windows/Mac clients.

## Core principle: two zones
Separate a **working/staging zone** from an **archive zone**. Never do dirty work inside the archive.
- **Staging** (`fast/_incoming/` or similar): external files land here first (WeChat/Telegram/camera/downloads exports).
- **Process** in staging: organize → md5 dedup → categorize.
- **Archive** (`vault/<topic>/`): only move finished, deduped, categorized files here.
- This keeps the archive clean by construction and makes "垃圾场" impossible.

## Workflow (validate with user before deleting anything)
1. **Inventory (read-only).** Size + file-type distribution per top-level dir. `du -sh * | sort -rh`, `find . -type f | sed 's/.*\.//' | sort | uniq -c`.
2. **Dedup (read-only report, never auto-delete).** Run `scripts/dedup_report.sh <dir>`. It prints duplicate hash groups + sample paths. Confirm with user which copy to keep.
3. **Categorize.** Move files into topic folders by content (e.g. 宝宝/婚礼/旅行/毕业 for a family-photo archive; 工程资料 for dwg/pdf; MKV/库 for video). Prefer filename-embedded dates for dating (camera `IMG_YYYYMMDD_HHMMSS`).
4. **Periodic review.** Set a cron (every 90d) that re-runs the dedup report and lists `_incoming` leftovers + deletable candidates. **Deletion always requires explicit user approval** — never auto-delete, especially sensitive archives.
5. **Remote goal.** User may want a NAS for deeper/redundant long-term storage; current server is the transitional store.

## Hard rules (this user)
- **Deleting/moving large batches**: always list a清单 first, get explicit 拍板 (approval), then execute and verify (re-count files, re-check bytes).
- **Sensitive archives stay hard-isolated**: 王浩纪念照片 (deceased-family photos), 基因/体检 (genetic/health) — only neutral organization (classify / cold-backup verify), NEVER delete, NEVER send to cloud models. (User relaxed cloud restriction for *project/work* files like CC_Switch/VAULT, but personal sensitive stays isolated — confirm which bucket a folder falls in before uploading to any API.)
- **No盲目装软件**: survey existing tools first; prefer现成 software over building.

## Pitfalls
- **Don't treat program dirs as data.** `anythingllm/`, `Microsoft VS Code/`, `LLM WIKI/llm-wiki.exe`, `node_modules/` are *software*, not "资料". When a user says "organize CC_Switch's files", the real asset is usually a sub-vault like `VAULT/` (an Obsidian vault with `wiki/` = compiled markdown). Separate the vault from the program files.
- **`_trash_review/`, `recovery-backup-*`, `_meta/`, `*.removed-*` are cleanup residue** from import/upgrade tools — safe to propose for deletion after listing, but confirm.
- **Obsidian "mess" is usually engine-output + raw + workspace intermixed**, not actual disorder. `wiki/` = compiled knowledge base (the good part); `raw/` = uncompiled sources; `.llm-wiki/` = config/cache. Keep `wiki/` + notes; the rest is staging/cache.
- **Hardware reality for LLM compilation**: a weak headless server (i5-6500, no GPU, ~6G RAM, AVX2 only) CAN run ollama but CPU-only 7B is ~2-5 tok/s — impractical. Do LLM-Wiki *compilation* on the user's stronger notebook or via cloud API; let the server be **storage + sync source** only. Obsidian on the client opens the server-shared vault over SMB/sync.
- **Chinese filenames + shell quoting**: paths with spaces/quotes/`'` break inline shell globs. Use Python (`os.walk`) or `find -print0 | xargs -0` to enumerate; avoid hand-typed globs on such trees.

## References
- `references/workflow-and-examples.md` — concrete example (this user's 3046: /data/fast vs /data/vault, VAULT anatomy, ollama hardware note).
- `scripts/dedup_report.sh` — md5 duplicate reporter (read-only, handles Chinese paths, parallel).


---

## 附：源技能 frontmatter（逐字存档）

```yaml
name: archive-hygiene
description: Organize/dedupe file archives so they stay junk-free.
```
