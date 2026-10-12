# Archive Hygiene — Concrete Example (this user, 2026-08-22)

## Topology
- **3046** (<hostname>, Ubuntu 24.04, i5-6500 no GPU, 7.7G RAM): Linux server / central store.
  - `/data/fast` (sdb, 458G) = **working/staging zone** → holds `_incoming/{微信,Telegram,相机,其他}` (created 2026-08-22).
  - `/data/vault` (sdc, 1.4T, 1.2T free) = **archive zone** → holds topic folders.
  - Has `docker` (daemon off by default) but NO `ollama`. SMB server runs (`[Kent]` share → /data/fast/Kent).
- **Notebook** (Windows, E: drive, stronger HW): source of `VAULT`, runs Obsidian + LLM-Wiki + AnythingLLM already. Mounted to 3046 at `/mnt/laptop_E` when online.
- **台式机** (Windows, administrator@): sometimes on, has its own Hermes instance repurposed as a thin client to 3046.

## File-management规范 (established 2026-08-22)
1. External files → `/data/fast/_incoming/` first.
2. Organize → md5 dedup → categorize in fast.
3. Move finished files into `/data/vault/<topic>/`.
4. Cron every 90d (`a8ef9e6d20aa`, deliver=all, next 2026-11-20) re-runs dedup + lists `_incoming` leftovers + deletable candidates. Deletion needs explicit user 拍板.

## VAULT anatomy (the "mess" the user couldn't read)
Path on 3046: `/data/fast/CC_Switch_v2/Kent'AI/VAULT/`
- `wiki/` → 3455 compiled markdown = the real knowledge base (Obsidian double-linked). **KEEP.**
- Root `.md` (欢迎/双机指南/转码纪律…) = user's own notes. **KEEP.**
- `raw/` = uncompiled import sources (合同 doc/pdf). **STAGING.**
- `.llm-wiki/`, `_meta/`, `maps/`, `taishiji share/` = config/cache. **CACHE.**
- `_trash_review/` (53MB+, 3× `llmwiki-import-cleanup-20260712`, `anythingllm-backup-preupgrade`) = cleanup RESIDUE → propose for deletion.
- `recovery-backup-20260804/`, `.stfolder.removed-20260802/` = sync-tool residue → propose for deletion.
- Sibling program dirs (NOT data): `LLM WIKI/llm-wiki.exe`, `anythingllm/` (1.8G), `Microsoft VS Code/` (2G), `node_modules/`. Keep separate from the vault.

## ollama hardware note (3046)
i5-6500, no dGPU, AVX2 present, ~6G free RAM. ollama CPU-only 7B q4 ≈ 2–5 tok/s — impractical for LLM-Wiki compilation. Decision: compile on the notebook or via cloud API (DeepSeek/GLM keys available; project files cleared for cloud by user 2026-08-22, but 王浩/基因/体检 stay isolated). 3046 = storage + sync only.

## Sensitive-isolation boundary (confirmed 2026-08-22)
- **Isolated / never cloud / never delete:** 王浩纪念照片 (22G+, deceased-family), 基因/体检 raw data.
- **Cloud-OK (user relaxed):** CC_Switch / VAULT / 工程资料 / 合同. Still require approval before any deletion.
