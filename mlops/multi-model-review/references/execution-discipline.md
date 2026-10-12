# 执行纪律（静默交付 / 直连绕 Clash / cookbook / 各类实操坑）

> **本文件是 `multi-model-review` 技能的支持文档。**
> 来源：2026-09-26 从 SKILL.md「执行纪律」整节下沉。

---

## 执行纪律
### 调用顺序铁律
默认: **DeepSeek(主审)** → **GLM-5.2(二审)** → **Qwen3.7+(三审)** → **Kimi(四审)** → **LongCat(兜底)**。某模型挂了跳过，继续下一个，直到凑满 ≥3 个有效响应。（全文见「用户铁律」章。）
### 静默交付，不刷屏（Silent delivery — user strongly dislikes output spam）
- Write all outputs to local `.md` files; **never print** to chat mid-pipeline.
- Run as a **cron `no_agent` script** with a long off-peak schedule; it writes files, doesn't message.
- If a pipeline must run in foreground, print only a one-line completion count.
- 命令循环即停（2026-08-18 用户原话"不要这样一直刷屏了"）——重试 ≥3 次仍卡同一错误就停手，改喂模型判断。
### 全上下文包
派任务给模型 B 时不传截断稿，传完整背景包（全局约束 + 已决策 + 已知坑 + 草稿）。全文见「三档用法 / 档1」。
### 直连绕 Clash（Direct API calling pattern, bypass Clash, handle limits）
Call GLM/DeepSeek **directly** — do NOT route through Nous Portal for these (Nous Portal 404s GLM models; also wastes Nous credits the user reserves for Sonnet).

- **GLM:** `https://open.bigmodel.cn/api/paas/v4/chat/completions` (NOT `api.z.ai` — that host 404s on `/v1` AND `/api/paas/v4`; verified 2026-08-16), key from `.env` `GLM_API_KEY`, models `glm-4.5-air` / `glm-4.7-flash`（历史；现役 `glm-5.2`）。
- **DeepSeek:** `https://api.deepseek.com/v1/chat/completions`, key from `.env` `DEEPSEEK_API_KEY`, model `deepseek-v4-flash`（历史；现役 `deepseek-chat`）。
- **Bypass proxy:** pass `proxies={"http": None, "https": None}` — these are domestic APIs; if they inherit the Clash `HTTP_PROXY` env they SSL-fail intermittently. Direct call is stable.
- **Rate limits (free tier is harsh):** expect `429` and **empty `content`** on longer outputs (model truncates to length, reasoning fills the budget). Mitigations:
  - Keep `max_tokens` modest (200–1000); ask for short output.
  - Retry with exponential backoff (12–20s × 5–8 attempts).
  - If all attempts return empty, **don't burn credits retrying forever** — bail and let a low-peak cron retry later.
  - Free-tier RPM is low and dynamic; long tasks often fail mid-run. Schedule heavy runs at low-peak (e.g. 03:00).
- **Verify before trusting:** check `r.json()["choices"][0]["message"]["content"]` exists; free tier sometimes returns no `choices` (404/empty) — handle KeyError.
### B ｜ 2026-08-23 直接调用 cookbook (3046 .env 已存 key, 直连不绕 Nous)
- DeepSeek: `https://api.deepseek.com/v1/chat/completions`, key `DEEPSEEK_API_KEY`, model `deepseek-chat` (实测返回 deepseek-v4-flash)。
- LongCat: `https://api.longcat.chat/openai/v1/chat/completions`, key `LONGCAT_API_KEY`, model `LongCat-2.0`。
- Kimi: `https://api.moonshot.cn/v1/chat/completions`, key `KIMI_API_KEY`.
  - **2026-08-24 实测阵容收敛**: 现仅3可用模型 `kimi-k3` / `kimi-k2.6` / `kimi-k2.7-code-highspeed` (查 `/v1/models` 确认). 旧 `kimi-k2`/`kimi-k2-turbo`/`moonshot-v1-8k/32k/128k` 全 404.
  - **强制 `temperature=1`**: 传 0.3 直接 400 `invalid temperature: only 1 is allowed`. 调用 Kimi 务必 `temperature=1` (首轮失败已验证).
  - **RPM=3 限流**: 超频返 429 或**空 content**(无 choices). 这是"Kimi 空响应"根因——非模型坏, 是端点限流. 对策: 重试退避(`time.sleep(2*(i+1))`×4~5), 仍空则不采纳, 记"Kimi 限流不可用", 以 DeepSeek主审+agent自验顶替, **绝不伪造其意见**.
- SiliconFlow (Qwen3-VL/Qwen2.5): `https://api.siliconflow.cn/v1/chat/completions`, key `SILICONFLOW_API_KEY`, model `Qwen/Qwen3-VL-8B-Instruct` / `Qwen/Qwen2.5-7B`。
- 读取 key 用 python 正则 `re.search(r'NAME=\s*(\S+)', env)`; 去引号 `.strip("'").strip('"')` 防 401。
- 取响应统一 `msg.get("content") or msg.get("reasoning_content")`。
- ⚠ 国内 API (deepseek/longcat/siliconflow) 直连即可; 勿继承 Clash `HTTP_PROXY` (用 `requests` 时 `trust_env=False` 或 `proxies={}`), 否则 SSL 间歇失败。
- 完整版见 `references/direct_api_cookbook.md` (已含 GLM/DS; 本场新增 longcat/kimi 同理直连)。
### key 探测姿势（B ｜ 2026-08-19）
`.env` 里 key 用 `grep` 可能漏(行尾/编码), 用 python 正则 `^KEY\s*=\s*(.+)` 才抓得到。本次用户说"已配置"但 grep 搜空, 实际 key 在(长度49/35)。读取须 strip 首尾引号。
### Pi 子进程 .env 继承坑（2026-09-18 实战）
- **现象**：Pi 子进程不继承 `~/.hermes/.env` 中的 key，调用 DeepSeek/GLM/Qwen 等模型时返回 "No API key found"
- **根因**：Hermes 的 `.env` 在 agent 启动时加载到 shell 环境，但 `delegate_task` 派生的 Pi 子进程是独立 session，不继承这些变量
- **修法**：`grep -E 'DEEPSEEK_API_KEY|GLM_API_KEY|DASHSCOPE_API_KEY|KIMI_API_KEY' $HOME/.hermes/.env > ~/.pi/agent/.env`，或派 Pi 任务时手动 `export KEY=$(grep ...) && pi ...`
- **影响**：多模型交叉审 job 失败、后台 silent 无输出、浪费排查时间
### SoL-Pi Evidence Reducer 模式（2026-09-14 学习）
来源：NVIDIA SoL-Pi (MIT) — 便宜模型先读日志，压缩为逐字证据后再给主模型。

**应用到交叉审**：
- 长日志/证据 → 先用 LongCat/DeepSeek-Flash 过滤压缩（¥0.1/M token）
- 压缩后证据 → 再喂主审模型（DS/Kimi）
- 省主审 50-70% 输入 token，结论质量基本不变

**触发条件**：单份证据 >2000 chars 或总证据 >8000 chars 时启用。
### 不要反复让用户手动执行（B ｜ 实操铁律, 本会话用户反复纠正, 已固化）
用户原话"不要老是让我来弄"。能自动化(脚本/SSH公钥免密/API)就自己跑完, 只把"必须用户物理操作"那一步(如插显示器/粘公钥)留给他且一次说清。反复让他贴命令到终端 = 失败。
### 慢≠卡死（B ｜ 2026-08-19 关键坑）
免费档 RPM/输出限制会让长审查返回空, 靠短 prompt + 双字段兜底 + 重试解决, 不是网络断了。
### 编程任务也走本路由（B ｜ 2026-08-19 用户明确）
编程工作 = GLM优先(深加工/写码) + DeepSeek审计 + SF兜底, 与交付物审查同链路。 **HY3 禁止用于编程**(用户实测 hy3 编程基本没搞好过)。实操用 aider+GLM 零成本(已验证 2.1k+2.8k token≈0元), GLM失联切 SiliconFlow Qwen3.5-35B。DS直连 api.deepseek.com 用于审计(用户满意且便宜)。
