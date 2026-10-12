# Pitfalls（追加）

> 2026-09-27 「文件整理簇」4→1 合并：本节从 `safe-file-organization/SKILL.md` 第 120–123 行**逐字**拆出。

## Pitfalls (additions)
- **Don't assume cloud-isolation uniformly**: a batch may be released to cloud; ask per batch which class it is.
- **Don't run ollama on 3046** for KB compile — hardware too weak; offload to laptop/cloud.
- **Windows map uses share NAME**, not filesystem path: user maps `\\192.168.99.X\Knowledge` where `Knowledge` is the `[Knowledge]` smb.conf section name, not `/data/vault/knowledge/VAULT`.


---

# 从主 SKILL.md 拆出（2026-09-27 文件整理簇合并，逐字）

- **别假设云隔离是统一的**：某一批可能被放行上云；**逐批问它属于哪一类**。
- **别在 3046 上跑 ollama** 做知识库编译——硬件太弱，卸载到笔记本/云。
- **程序目录不是数据**：`anythingllm/`、`Microsoft VS Code/`、`LLM WIKI/llm-wiki.exe`、`node_modules/` 是**软件**不是"资料"。
- **`_trash_review/`、`recovery-backup-*`、`_meta/`、`*.removed-*`** 是导入/升级工具的清理残渣——列清单后可提议删除，但要确认。
- **Obsidian 的"乱"通常是引擎产物 + 原始文件 + workspace 混在一起**：`wiki/` = 编译好的知识库（好东西，**留**）；
  `raw/` = 未编译源（暂存）；`.llm-wiki/` = 配置/缓存。


---

# 从主 SKILL.md 拆出的 Pitfalls（2026-09-27，逐字）

- **scp 到 Windows OpenSSH 绝对路径**（`C:\...`）常被误解。优先 PowerShell `EncodedCommand` 内嵌 base64，或一个把 base64 解成精确路径的 ps1。

- **从 Windows 搬来的文件 Permission denied**：SMB/桌面拷来的目录属主是 `administrator` 不是 `hermes`，`mv` 失败。
  用 `sudo chown -R hermes:hermes <dir>` **在顶层修一次**，而不是给每个 `mv` 加 `sudo`。

