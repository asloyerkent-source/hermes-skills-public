# Standing pipeline（用户 2026-08-22 定义）

> 2026-09-27 「文件整理簇」4→1 合并：本节从 `safe-file-organization/SKILL.md` 第 94–101 行**逐字**拆出。

## Standing pipeline (user-defined 2026-08-22)
External files (WeChat/Telegram/camera/downloads/project exports) follow a fixed flow — do NOT drop them straight into `/data/vault` topic folders:
1. **Ingress**: land in `/data/fast/_incoming/` (subdirs: 微信/Telegram/相机/其他). This is the staging area.
2. **Process in fast**: inventory → md5 dedup → clean → classify. Never do dirty work inside `/data/vault`.
3. **Archive**: once processed, move into the matching `/data/vault/` topic folder (宝宝/婚礼/旅行/毕业/工程资料/MKV库/VAULT).
4. **fast = workbench, vault = archive.** Keep it that way.
5. **Quarterly review**: a cron (every 90d, `deliver='all'`) re-runs md5 dedup across vault + checks `_incoming` backlog + proposes deletable items. **Report only — never auto-delete.** Next fire: 2026-11-20 (job id logged in progress.md).
6. **Long-term goal**: NAS takes over large-file cold storage; 3046 vault (1.4T) is transitional.
