# original-safe-file-organization-en — 本技能合并前的原 SKILL.md 正文（逐字，英文）

> 2026-09-27 「文件整理簇」4→1 合并：主 SKILL.md 已重写为中文整合版（§0-§7）。
> **本文件是重写前的原文，逐字保留**——重写会不可逆地丢信号（同日 `房产簇` 实测：改写丢 6 行精确字符串、
> 两张同义表被误判为超集丢了 `挂牌价`/`理财`/`投房` 三个词）。原文留档，便于逐条比对。
> 源目录未归档（本技能就是合并目标），此文件即其原文的唯一活动副本；备份 `~/.hermes/skill-backups/merge-cleanup-20260927-001231/safe-file-organization/`。

# Safe File Organization

## When to use
- User wants a messy directory (often 3046's `/data/vault` or `/data/fast`) cleaned, classified, or deduped.
- Data may mix: personal archives, engineering files (dwg/pdf/rps/skp), social exports (Telegram/WeChat), camera rolls, and **sensitive irreplaceable** items (family photos, health/genetic — never bulk-move or delete without explicit say-so).
- Trigger phrases: "整理一下这些文件", "不能变垃圾场", "归个类", "看看有重复的么", "移到X那边去".

## Hard rules (non-negotiable)
1. **Read-only inventory FIRST.** Never move/delete before you know what's there: `du -sh`, `find ... -printf`, file-type histogram, total count.
2. **No delete without explicit confirmation.** Especially sensitive/irreplaceable data. Report duplicates; let the user choose keep-both (redundancy) or delete-one. When in doubt, keep.
3. **Batch approval, then execute.** Present plan as **A** (light cleanup: empty shells, stale .lnk) / **B** (categorize: move scattered files, date-sort camera roll) / **C** (deep: knowledge-base / Obsidian / RAG). Get per-batch go-ahead. Once a batch is approved, execute it without re-asking per file.
4. **Defer deep work (C).** User may say "先A+B，C到时候我提". Gather the full inventory during A+B so you can answer C instantly later — don't redo discovery.
5. **Verify, don't assume.** After moving: count source vs dest files, confirm source root is empty, check for nested-dir bugs, re-read actual paths (not assumptions).

## Workflow
1. **Inventory (read-only)**: top-level dirs + sizes, file-type histogram, total count, identify Windows build artifacts (`node_modules`) mistakenly stored as data.
2. **Identify**: empty shells, duplicate trees, scattered files at a dir's root, permission owner mismatches.
3. **Propose plan A/B/C** with risk labels. Wait for approval.
4. **Execute approved batch**; verify each step with real output (counts, `ls`).
5. **Dedup pass (MD5)** — report only, never auto-delete.
6. Optionally update progress notes / memory if structure changed.

## Techniques (see references/techniques.md)
- Filename-date categorization (`IMG_YYYYMMDD_HHMMSS`, `VID_`, `video_`, `ptYYYY_MM_DD` patterns)
- MD5 duplicate detection (report-only)
- Windows-origin permission fix (`sudo chown` — hermes has passwordless `sudo -n`)
- Terminal `cd H:\\Hermes` ghost error → pass `workdir=/` to the terminal tool

## Deduplication ordering (user-corrected 2026-08-26, reinforced 2026-09-02)
When checking whether two trees overlap, **do NOT start with a full MD5 scan** — on a slow
archive disk (HDD) with thousands of files, `find ... -exec md5sum` times out in the
foreground (180s) and wastes the user's time. The user corrected: "先对文件名是不是一样的，
再对哈希数是不是比较合理". Correct order, cheapest-first:

1. **Filename match** (pure string, instant): `find ... -printf "%f\n" | sort -u` on both
   sides, `comm -12` for overlaps. Phone-origin files (`IMG_20240308_172939.jpg`) vs
   renamed archives almost never share names → expect 0 here, which is itself a fast signal.
2. **File-size match** (stat only, fast): extract `size\tpath`, `sort -n`, `join` on size.
   If size sets have **0 overlap**, content cannot be identical (same bytes ⇒ same size) →
   you can stop and report "no duplicates" with high confidence **without any hashing**.
3. **SHA256 only for size-matched candidates** (the only pairs worth hashing). Or, for a
   statistical confidence check without a full scan, **sample 5 random files**, hash them,
   and grep against the other tree's full hash list — cheap and catches the obvious case.

This ordering turned a 180s timeout into a 2-second conclusion in the 3046 session
(Camera 6351 photos vs vault 4791 photos: 0 filename overlap, 0 size overlap ⇒ not
duplicated, confirmed by a 5-file random sample).

### 2026-09-02 实战强化：跨目录去重
用户要求清理 `E:\kent` 和 `E:\kent\Pictures` 之间的重复文件。
- **不要用 LLM 做文件去重**：11,000+ 文件 / 48GB，LLM 看几个月都看不完
- **正确做法**：Python 脚本按 size → SHA256 两阶段筛选，纯哈希计算零 token 消耗
- 脚本模板见 `scripts/dedup_find.py`（size 初筛 + SHA256 确认 + JSON 报告输出）
- 生成删除脚本时也走同样逻辑：按修改时间排序，保留最早一份

## Photo-library structure (built 2026-08-26, user-approved pattern)
For a personal photo hoard that must stay browsable (not a "垃圾堆"), build a year/event
tree with a per-folder cloud/local marker so sensitive batches stay offline:
```
/data/vault/照片库/
  2018/ .meta.json            # {"year":2018,"cloud":false,"note":"..."}
  2024/
    .meta.json
    博恩泡泡球验货/             # user-named event subfolder
      .meta.json               # {"cloud":false,"note":"博恩业务,不含私料"}
      IMG_xxx.jpg
    春节老家/
      .meta.json               # {"cloud":true,"note":"家庭照可上云"}
```
- **Auto-year by EXIF** (not filename guessing): `exiftool -DateTimeOriginal` → `YYYY`;
  install `libimage-exiftool-perl` on Ubuntu. Phone files usually have NO GPS, so
  location-auto-sort is unreliable — fall back to user-named event subfolders.
- **`.meta.json` carries the cloud/local rule** per folder — this is the user's requested
  "备注这个文件夹不能出本地或者可以上云" mechanism. Default `cloud:false`.
- **Semi-auto (user choice C)**: agent does EXIF year-sort + moves; user later drags into
  event subfolders and writes `.meta.json`. Don't try full content-AI-classification
  locally — 3046's P620 (2GB VRAM) can't run vision models; cloud vision API violates the
  red line for sensitive photos.
- **Red-line**: 王浩纪念照片 stays OUT of this library's open tree until the user explicitly
  says to fold it in; if folded, its folder `.meta.json` must be `cloud:false`.
- See `references/photo_library.md` for the exact EXIF-year move script.

## Pitfalls
- **Nested directory bug**: `cd` then `mkdir Camera/YYYY-MM` creates `Camera/Camera/YYYY-MM`. Always use absolute target paths with `mkdir -p`.
- **scp to Windows OpenSSH absolute path** (`C:\...`) is often misinterpreted. Prefer PowerShell `EncodedCommand` with embedded base64, or a ps1 that decodes base64 to the exact path.
- **Sensitive data isolation**: never fold family/health archives into generic trees silently; keep them separate and tell the user.
- **Permission denied on moved-from-Windows files**: dirs copied from Windows SMB / desktop are owned by `administrator`, not `hermes`. Fix once with `sudo chown -R hermes:hermes <dir>` rather than `sudo`-ing every `mv`.

## Standing pipeline (user-defined 2026-08-22)
External files (WeChat/Telegram/camera/downloads/project exports) follow a fixed flow — do NOT drop them straight into `/data/vault` topic folders:
1. **Ingress**: land in `/data/fast/_incoming/` (subdirs: 微信/Telegram/相机/其他). This is the staging area.
2. **Process in fast**: inventory → md5 dedup → clean → classify. Never do dirty work inside `/data/vault`.
3. **Archive**: once processed, move into the matching `/data/vault/` topic folder (宝宝/婚礼/旅行/毕业/工程资料/MKV库/VAULT).
4. **fast = workbench, vault = archive.** Keep it that way.
5. **Quarterly review**: a cron (every 90d, `deliver='all'`) re-runs md5 dedup across vault + checks `_incoming` backlog + proposes deletable items. **Report only — never auto-delete.** Next fire: 2026-11-20 (job id logged in progress.md).
6. **Long-term goal**: NAS takes over large-file cold storage; 3046 vault (1.4T) is transitional.

## Knowledge-base (Obsidian + LLM-Wiki) extraction
Project dirs like `CC_Switch_v2` mix real assets with program files. Separate them:
- **Real assets**: Obsidian vaults / compiled `wiki/` markdown (e.g. `VAULT` → 3455 .md). Extract to `/data/vault/knowledge/<NAME>/`.
- **Program files (NOT data)**: `node_modules/`, `*.exe`, `anythingllm/`, `Microsoft VS Code/`, `llm-wiki.exe` — leave in place or archive separately; never treat as "资料".
- **Junk to clean (after user OK)**: `_trash_review/` (import-residue), `recovery-backup-*`, `.stfolder.removed-*`, `_meta` caches.
- **Serve over SMB**: add a `[Share]` section in `/etc/samba/smb.conf` → the extracted vault; laptop Obsidian opens `\\192.168.99.X\Share`. Verify with `sudo smbstatus` that the laptop (192.168.99.X) actually mounted it.
- **3046 is storage, not compute**: i5-6500, no GPU, ~6G RAM → local `ollama` is impractical (CPU-only, slow). Keep model compilation/querying on the laptop's existing toolchain (Obsidian+llm-wiki+AnythingLLM) or cloud API. 3046 only hosts the markdown + SMB sync.

## Red-line nuance (per-batch, not blanket)
- Default: family/health/genetic archives (王浩纪念照片, 基因/体检) are **hard-isolated, never to cloud, never bulk-delete**.
- BUT the user can **explicitly release a batch**: "CC_Switch/VAULT 这批可以上云" relaxes the rule *for that batch only*. Confirm which class each new batch belongs to; don't assume the blanket rule OR the relaxation applies globally.

## Techniques (additions)
- **Apostrophe/space paths**: `Kent'AI`, `王浩纪念照片` break shell quoting. Use a `from hermes_tools import terminal` + `os.walk` Python block instead of `terminal` for listing/moving — Python handles Unicode/apostrophe paths natively. (Reserve `terminal` for paths without such chars; pass `workdir=/` to dodge the `cd H:\Hermes` ghost.)
- **SMB client verify**: `sudo smbstatus -S` shows connected machines + share; `smbclient //127.0.0.1/Share -U administrator%333 -c "ls"` tests readability/writability from the 3046 side.
- **md5 dedup across two trees**: `find A -type f -exec md5sum {} \; | sort | uniq -c` then `comm` on name/hash sets to *prove* 100% identical before deleting one side.

## Pitfalls (additions)
- **Don't assume cloud-isolation uniformly**: a batch may be released to cloud; ask per batch which class it is.
- **Don't run ollama on 3046** for KB compile — hardware too weak; offload to laptop/cloud.
- **Windows map uses share NAME**, not filesystem path: user maps `\\192.168.99.X\Knowledge` where `Knowledge` is the `[Knowledge]` smb.conf section name, not `/data/vault/knowledge/VAULT`.

## References
- `references/techniques.md` — exact command patterns (inventory, chown, date parsing, MD5 dedup, terminal ghost fix).
- `references/knowledge_base_smb.md` — VAULT extraction + SMB `[Knowledge]` share setup + 3046 hardware constraint.
- `references/photo_library.md` — EXIF-year photo move script + `.meta.json` cloud/local marker schema (used 2026-08-26).
- `references/remote-cleanup-workflow.md` — 远程机器清理标准流程（诊断→分类→方案→执行+验证，2026-09-02 3046实测）.
- `scripts/organize_by_date.sh` — template for filename-date categorization (DRY-run safe).
- `scripts/find_dupes.sh` — template for MD5 duplicate report (never deletes).


---

## 附：原 frontmatter（逐字存档）

```yaml
name: safe-file-organization
description: Organize 3046 dirs. Inventory first, no delete without OK.
```
