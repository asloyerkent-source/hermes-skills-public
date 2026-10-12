# 知识库（Obsidian + LLM-Wiki）提取

> 2026-09-27 「文件整理簇」4→1 合并：本节从 `safe-file-organization/SKILL.md` 第 103–109 行**逐字**拆出。

## Knowledge-base (Obsidian + LLM-Wiki) extraction
Project dirs like `CC_Switch_v2` mix real assets with program files. Separate them:
- **Real assets**: Obsidian vaults / compiled `wiki/` markdown (e.g. `VAULT` → 3455 .md). Extract to `/data/vault/knowledge/<NAME>/`.
- **Program files (NOT data)**: `node_modules/`, `*.exe`, `anythingllm/`, `Microsoft VS Code/`, `llm-wiki.exe` — leave in place or archive separately; never treat as "资料".
- **Junk to clean (after user OK)**: `_trash_review/` (import-residue), `recovery-backup-*`, `.stfolder.removed-*`, `_meta` caches.
- **Serve over SMB**: add a `[Share]` section in `/etc/samba/smb.conf` → the extracted vault; laptop Obsidian opens `\\192.168.99.X\Share`. Verify with `sudo smbstatus` that the laptop (192.168.99.X) actually mounted it.
- **3046 is storage, not compute**: i5-6500, no GPU, ~6G RAM → local `ollama` is impractical (CPU-only, slow). Keep model compilation/querying on the laptop's existing toolchain (Obsidian+llm-wiki+AnythingLLM) or cloud API. 3046 only hosts the markdown + SMB sync.
