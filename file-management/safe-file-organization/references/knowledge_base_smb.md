# Knowledge Base over SMB — 3046 recipe (from 2026-08-22 VAULT session)

## When
User wants Obsidian + LLM-Wiki knowledge base consolidated on 3046 and opened on the laptop.

## Step 1 — Extract real assets, leave program files
Project dirs (e.g. `/data/fast/CC_Switch_v2`) mix assets and software:
- **Assets** (move to `/data/vault/knowledge/<NAME>/`): Obsidian vault roots, compiled `wiki/` dirs (3455 .md for VAULT), root-level notes.
- **Program files** (do NOT treat as data): `node_modules/`, `*.exe`, `anythingllm/`, `Microsoft VS Code/`, `llm-wiki.exe` (under `LLM WIKI/`).
- **Junk** (clean after user OK): `_trash_review/` (import residue, ~66MB), `recovery-backup-*`, `.stfolder.removed-*`, `_meta`.

## Step 2 — Python, not shell, for Unicode/apostrophe paths
Paths like `Kent'AI`, `王浩纪念照片` break shell quoting. Use:
```python
from hermes_tools import terminal
import os, shutil
src = "/data/fast/CC_Switch_v2/Kent’AI/VAULT"   # note ’ (U+2019) not '
dst = "/data/vault/knowledge/VAULT"
shutil.move(src, dst)        # atomic; verify count after
```
Verify: `find dst -name '*.md' | wc -l` matches expected; root listing sane.

## Step 3 — SMB share + laptop Obsidian
Add to `/etc/samba/smb.conf` (needs `sudo bash -c 'cat >> ...'`; plain append is Permission-denied):
```
[Knowledge]
   path = /data/vault/knowledge/VAULT
   browseable = yes
   read only = no
   guest ok = no
   valid users = administrator
   force user = hermes
```
Then: `sudo systemctl reload smbd`. Test from 3046:
`smbclient //127.0.0.1/Knowledge -U administrator%333 -c "ls"` (credentials: administrator / 333 — the 3046 SMB account, NOT wifi password).

## Step 4 — Verify laptop actually mounted (don't trust self-report)
`sudo smbstatus -S` shows connected machine IP (laptop = 192.168.99.X) + share name. Locked-files list confirms Obsidian opened `wiki/...` notes. Only then declare success.

## Hardware constraint (load-bearing)
3046 = i5-6500 (4c/4t, no HT), Intel HD 530 (no CUDA), ~6G free RAM. Local `ollama` is CPU-only and impractical for 7B+ (slow). So:
- 3046 = central markdown store + SMB sync ONLY.
- Compile/query the wiki on the laptop (Obsidian + llm-wiki.exe + AnythingLLM already installed) or via cloud API (DeepSeek/GLM) — and only for batches the user has released to cloud.

## Red-line per batch
Default: 王浩纪念照片 / 基因 / 体检 = hard-isolated, never cloud, never bulk-delete.
User may release a specific batch ("CC_Switch/VAULT 这批可以上云") — relaxation is batch-scoped, confirm each new batch's class.
