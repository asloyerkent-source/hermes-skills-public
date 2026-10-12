# 模型端点实测行为（合并：2026-08 ～ 2026-09）
> **合并说明（2026-09-26）**：本文件由 3 个源 ref 按日期分节归并而成，**所有条目原样保留**（未删任何一条）：
> - `references/model-endpoint-quirks-2026-08.md`
> - `references/model-endpoint-quirks-2026-09-14.md`
> - `references/provider-quirks-2026-08-24.md`（本簇归档目录内未留副本；原件在 `~/.hermes/skill-backups/merge-cluster1-20260926_163644/multi-model-review.bak-*/references/`）

---

# ① model-endpoint-quirks-2026-08.md（2026-08-24 会话实测）

# 模型端点实测行为 (2026-08-24 会话实测)

## 端点汇总
- LongCat: `https://api.longcat.chat/openai/v1/chat/completions`, model `LongCat-2.0`, key 在 `~/.hermes/.env` LONGCAT_API_KEY
- DeepSeek: `https://api.deepseek.com/v1/chat/completions`, model `deepseek-chat`, DEEPSEEK_API_KEY
- Kimi: `https://api.moonshot.cn/v1/chat/completions`, models `kimi-k2.6`/`kimi-k3`/`kimi-k2.7-code-highspeed`, KIMI_API_KEY

## 实测行为
### LongCat-2.0
- 经常性空响应：HTTP 200 但 `choices[0].message.content` 为空字符串。
- 原因未知（可能推理模型默认不回 content，或负载问题）。
- 处理：重试 1–2 次仍空 → 标记"调用失败不采纳"，用 DeepSeek + 源码验证顶上。

### DeepSeek (deepseek-chat)
- 最稳定，主审首选。返回完整结构化结论。
- temperature 可传 0.2 等低值。

### Kimi 系 (k2.6 / k3 / k2.7-code-highspeed)
- **强制 temperature=1**：传 0.3 等报 `invalid_temperature: only 1 is allowed for this model`。
- **RPM=3 限流**：超频返回 429 `Rate limit exceeded` 或空响应。
- 可用模型列表（`/v1/models` 实测）：`kimi-k2.7-code-highspeed`, `kimi-k2.6`, `kimi-k3`。旧 `moonshot-v1-*` 全 404。
- 重试模板：
  ```python
  for i in range(retries):
      r = requests.post(url, headers={...}, json={...,"temperature":1,"max_tokens":900}, timeout=150)
      j = r.json(); c = j["choices"][0]["message"]["content"]
      if c: return c
      if "Rate limit" in j.get("error",{}).get("message",""):
          time.sleep(2*(i+1)); continue
      return c or f"[空] {j.get('error')}"
  ```

## 关键教训
- **模型互审也会错**：本轮 DeepSeek 主审猜"Holographic 信任评分误伤低频事实"，读插件源码验证不成立。务必以一手资料/源码为准。
- **并发测试假阳性**：threading 同进程边写边读同一文件，读到半行误报"全损坏"。追加写安全验证须独立进程顺序写+独立读。
- **不硬等限流端点**：某模型持续空响应，记录失败、用其他模型+实证顶上，不反复重试烧额度。

---

# ② model-endpoint-quirks-2026-09-14.md（3046 无头服务器, 2026-09-14 / 2026-09-17 更新）

# 多模型端点实测行为 (3046 无头服务器, 2026-09-14)

本会话在 3046 (<hostname>, Ubuntu 24.04) 用新 key 实测多模型直连。
覆盖并取代 `model-endpoint-quirks-2026-08-30-3046.md`（旧版信息）。

> **2026-09-17 更新**：原七牛云聚合层（`api` 聚合端点）账户 billing 暂停，全部端点下线；原经它路由的 GPT-4o-mini / Gemini 一並移除，改由 **Qwen3.7+ (DashScope)** 承担。本文件下方关于聚合层的记录已标为下线。

## 2026-09-14 实测结果

```
set -a; source ~/.hermes/.env; set +a
curl -s -o /dev/null -w "%{http_code}" -m 10 \
  -X POST "<endpoint>/chat/completions" \
  -H "Authorization: Bearer $KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"<model>","messages":[{"role":"user","content":"hi"}]}'
```

| 模型 | Provider | Endpoint | HTTP | 备注 |
|---|---|---|---|---|
| **LongCat-2.0** | longcat | api.longcat.chat/openai/v1 | 200 ✅ | 免费资源包（等价备用：nous `meituan/longcat-2.0:free`） |
| **DeepSeek** | deepseek | api.deepseek.com/v1 | 200 ✅ | 主审，直连通 |
| **Kimi K2.7 Code** | kimi | api.moonshot.cn/v1 `kimi-k2.7-code` | 200 ✅ | 限 3 RPM，并行易 429，失败即跳过 |
| **GLM-5.2** | glm | open.bigmodel.cn/api/paas/v4 | 200 ✅ | `glm-5.2`（provider glm） |
| **Qwen3.7+** | dashscope | dashscope.aliyuncs.com/compatible-mode/v1 | 200 ✅ | `qwen3.7-plus`（阿里云百炼） |

## DeepSeek 直连 (新 key)
- 2026-09-14 用户提供新直连 key → 直连 200
- 旧版记录"3046 无 key"已过时
- 模型: `deepseek-chat` (非 deepseek-v4-flash)

## Kimi 直连（2026-09-17 更新）
- 直连 `api.moonshot.cn/v1`，`kimi-k2.7-code`，**限 3 RPM**
- 原经聚合层的路由已随聚合层下线（2026-09-17）取消
- 并行调用时 Kimi 最易 429，失败即跳过不重试；`temperature` 必须=1

## 聚合层 — 已下线（2026-09-17）
- 原七牛云聚合账户 billing 暂停，`api` 聚合端点全部不可用
- 原先借它路由的 GPT-4o-mini / Gemini 一並移除
- **替代**：Qwen3.7+ `dashscope.aliyuncs.com/compatible-mode/v1`（`DASHSCOPE_API_KEY`）

## LongCat (Nous 平台)
- 之前记录"LongCat content 字段缺失"是 api.longcat.chat 端点的问题
- 实际主力是 Nous 平台的 `meituan/longcat-2.0:free`，直连正常

## 调用脚本模板

```bash
set -a; source ~/.hermes/.env; set +a

# 直连 DeepSeek
curl -s -X POST "https://api.deepseek.com/v1/chat/completions" \
  -H "Authorization: Bearer $DEEPSEEK_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"deepseek-chat","messages":[...],"max_tokens":2000}'

# 直连 Kimi（限 3 RPM）
curl -s -X POST "https://api.moonshot.cn/v1/chat/completions" \
  -H "Authorization: Bearer ***" \
  -H "Content-Type: application/json" \
  -d '{"model":"kimi-k2.7-code","temperature":1,"messages":[...],"max_tokens":2000}'

# 直连 GLM-5.2
curl -s -X POST "https://open.bigmodel.cn/api/paas/v4/chat/completions" \
  -H "Authorization: Bearer ***" \
  -H "Content-Type: application/json" \
  -d '{"model":"glm-5.2","messages":[...]}'

# 直连 Qwen3.7+ (DashScope)
curl -s -X POST "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions" \
  -H "Authorization: Bearer ***" \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen3.7-plus","messages":[...]}'
```

## execute_code 沙箱坑 (仍有效)
- `execute_code` Python 沙箱拿不到 shell env → key 在沙箱里 KeyError
- 解法: 脚本写文件后用 **终端** `python3` 跑

## 实际可用阵容 (2026-09-17 更新)
- 直连: DeepSeek + GLM-5.2 + Qwen3.7+ + Kimi + LongCat = 5 个独立模型
- 原聚合层已下线（billing 暂停），不再计入
- 关键决策: 5 模型齐全（权重 3+2+2+2+1 = 10）
- 成本: 远低于 ¥50/月（国内模型微量调用几分钱）

---

# ③ provider-quirks-2026-08-24.md（Provider Quirks & Verification Engineering — 2026-08-24 session）

# Provider Quirks & Verification Engineering — 2026-08-24 session

Condensed from a live multi-model verification session (DeepSeek Harness research + evo_events.py trajectory-code audit). Updates the roster in `longcat_qwen_vision_quirks.md`.

## 1. Kimi endpoint status (CHANGED since 2026-08-23 doc)
- Available models now: **only 3** — `kimi-k3`, `kimi-k2.6`, `kimi-k2.7-code-highspeed`. Old `moonshot-v1-*` all 404.
- **All force `temperature=1`** (k3, k2.6, k2.7-code) — passing 0.3 → 400 `invalid temperature: only 1 is allowed`. Already noted for k2.6; now confirmed for the whole family.
- **RPM = 3** (org-level). Exceeding → `429 "Organization Rate limit exceeded"`. This is why Kimi returned **empty `content`** this session on every call (not a model bug — rate-limited to empty).
- Practical consequence: **Kimi is NOT a reliable real-time 二审** when you also call it for other things in the same minute. For a multi-model audit, alternate models or back off.
- Workaround used: retry with `time.sleep(2*(i+1))`, but RPM=3 means even retries contend. **Conclusion: when Kimi is rate-limited/unavailable, do NOT fabricate its opinion — rely on DeepSeek主审 + agent self-verify, and note "Kimi unavailable, not adopted".**

## 2. LongCat empty responses (NEW note)
- `LongCat-2.0` returned **empty `content` AND empty `reasoning_content`** on the dsh analysis call this session (the doc only warned about reasoning-in-reasoning_content and fabrication, not outright empty).
- Mitigation: never treat a single LongCat empty as "done". If it's the draft model, re-issue or fall back. For the audit chain, **DeepSeek `deepseek-chat` was the stable, complete responder** this session — keep it as the reliable主审.

## 3. DeepSeek = reliable主审 (confirmed)
- `deepseek-chat` returned a complete, high-quality audit (caught 4 real bugs in evo_events.py: missing concurrency lock, stats() undercount, ms-precision timestamps, token_est method annotation). Use it as the audit anchor; LongCat/Kimi are supplementary.

## 4. Concurrent append fix (verification engineering)
- Naive `fcntl.flock` on the open file descriptor is **process-level only** — it does NOT serialize threads in the **same process** (POSIX flock is per-open-file-description; same-process threads share it, so a second thread acquires the same lock).
- Symptom observed: a 4-thread in-process write test interleaved/corrupted lines (misread as "86/287 lines corrupt" — that was a test-harness false positive; real cross-process flock works, but same-process threads still race).
- **Fix that passed a clean 92-line concurrent write with 0 corruption**: combine `threading.Lock()` (serializes same-process threads) + `fcntl.flock(LOCK_EX)` (serializes cross-process) around the `open/write/flush` block. Also add `f.flush()` before releasing the lock.
- If you only ever write from one process at a time, plain `fcntl.flock` is fine; add the threading.Lock the moment a single process uses threads (e.g. a test, or an agent loop with parallel tool calls).

## 5. Hermes file-tool path-resolution quirk (recurred ~6× this session)
- `patch` / `read_file` / `write_file` **intermittently fail** on absolute paths under `$HOME/...` with an error that mangles the path into a Windows-style prefix like `H:\Hermes\home\hermes\...` (e.g. `"Failed to read file: $HOME/.hermes/principles/principles.jsonl"` → next attempt shows `H:\Hermes$HOME/...`).
- The **retry with the identical absolute path succeeds**. No env change needed — it's a transient path-normalization glitch in the tool layer.
- **Mitigation**: when a file tool errors on an absolute path, just re-issue the same call; do not "fix" the path by adding/removing prefixes (that makes it worse). `terminal` + `cat`/`python` is a reliable fallback for reads.
- This is a tooling quirk, NOT a missing-binary/setup failure — capture the retry pattern, not a "tool is broken" constraint.

## 6. Token-cost honesty (reinforced)
- Local `len(text.split())` style token estimates are NOT real cost. The user's LongCat package (~59.9M tokens, balance 9.9046M + 50M resource pack, expires 2026-09-22) is the **real** budget; vendor bill is the only source of truth.
- When a model call returns empty due to rate-limit, that still may have consumed quota — don't assume "empty = free".

---

