

---

# 从主 SKILL.md 拆出（2026-09-27 文件整理簇合并，逐字）

## §6 环境事实（3046，2026-08 确认）

- **3046**（<hostname>, Ubuntu 24.04, i5-6500 无 GPU, 7.7G RAM）：Linux 中心存储。
  `/data/fast`（sdb 458G）= **工作/暂存区**；`/data/vault`（sdc 1.4T, 1.2T free）= **归档区**。
  有 `docker`（默认关）但**没有 `ollama`**。SMB 服务在跑（`[Kent]` → `/data/fast/Kent`）。
- **笔记本**（Win, E: 盘，硬件更强）：`VAULT` 的来源，已跑 Obsidian + LLM-Wiki + AnythingLLM；在线时挂到 3046 的 `/mnt/laptop_E`。
- **台式机**（Win, `administrator@`）：偶尔在线，自己的 Hermes 实例已改造成 3046 的瘦客户端。
- **3046 是存储不是算力**：本地 `ollama` 跑 7B q4 约 2-5 tok/s，不实用 → LLM-Wiki 编译放笔记本或云端 API，3046 只托管 markdown + SMB 同步。
- **SMB 凭据**：`administrator / 333`（**3046 的 SMB 账号，不是 wifi 密码**）；验证 `sudo smbstatus -S`；
  `smbclient //127.0.0.1/Knowledge -U administrator%333 -c "ls"`。
- **Windows 映射用的是共享名**，不是文件系统路径：用户映射 `\\192.168.99.X\Knowledge`，`Knowledge` 是 smb.conf 的 `[Knowledge]` 段名，不是 `/data/vault/knowledge/VAULT`。
