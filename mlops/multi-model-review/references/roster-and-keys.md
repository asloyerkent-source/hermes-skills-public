# 模型池 · key 现状 · 阵容历史

> **本文件是 `multi-model-review` 技能的支持文档。**
> 来源：2026-09-26 从 SKILL.md「模型池与 key 现状」整节下沉。⚠️ **key 与阵容会过期，引用前必须真调一次验证。**

---

## 模型池与 key 现状

调用前 `set -a; source $HOME/.hermes/.env; set +a` 加载 key。完整状态板见 `~/.hermes/references/model-status-board.md`（路由 skill 共用）。（A 原文；该旧路径 `~/.hermes/references/` 现已不存在，现行文件为 `references/model-status-board.md`。）
### 当前可用 key（2026-09-17 实测，**以此为准**）
完整状态板见 `references/model-status-board.md`（路由 skill 共用；本节是其摘要）。

**直连模型（五路并行池，总权重 10）**：
- **DeepSeek** ✅ `api.deepseek.com/v1` `deepseek-flash`（= DeepSeek-V4.1-Flash，1M 上下文，effort low/high/max，支持图片；旧名 `deepseek-chat` 仍可调但已不在 `/v1/models` 列表，响应体回 `deepseek-flash`。主审，推理深、代码准，权重 3）。另有 `deepseek-v4-pro`（= DeepSeek-V4-Pro）。
- **GLM-5.2** ❌ `open.bigmodel.cn/api/paas/v4` `glm-5.2`（2026-09-27 实测 HTTP 429「余额不足或无可用资源包，请充值」，暂不可用；充值后本条作废需重测）
- **Qwen3.7+** ✅ `dashscope.aliyuncs.com/compatible-mode/v1` `qwen3.7-plus`（阿里云百炼，keyenv `DASHSCOPE_API_KEY`，权重 2）
- **Kimi** ✅ `api.moonshot.cn/v1` `kimi-k2.7-code`（keyenv `KIMI_API_KEY`，限 3 RPM，`temperature` 必须=1，权重 2）
- **LongCat** ✅ `api.longcat.chat/openai/v1` `LongCat-2.0`（免费资源包 2026-09-22 到期，keyenv `LONGCAT_API_KEY`，权重 1）；等价备用通道 `inference-api.nousresearch.com/v1` `meituan/longcat-2.0:free`（`NOUS_API_KEY`）

**已移除 / 未配置（勿引用）**：
- **原七牛云聚合层** ❌ 账户 billing 暂停（2026-09-17），全部聚合端点下线；原经它路由的 GPT-4o-mini / Gemini 一并失效，改由 Qwen3.7+ 承担
- **HY3** ⚠️ 免费档已过期（付费版仍在，非默认池成员）
- **MiniMax** ❌ 从未配置端点，不入池
- **Nous Sonnet** ❌ 从未使用，未配置路由
- **GPT-4o-mini / Gemini** ❌ 随聚合层下线

**探活**：跑 `scripts/model_key_health.sh` 探活；≥3 个返回 200 才 PROCEED（退出码 0）。
### 历史注记 ｜ B ｜ 2026-08-23 ROSTER UPDATE — GLM deprecated, LongCat/Kimi/Qwen3-VL added
> User explicitly deprecated GLM this session ("GLM体验差彻底弃用"). Live review roster is now:
> **DeepSeek V3 (主审/验证) + LongCat-2.0 (执行三审/跨文档/代码) + Kimi K2.6 (代码二审) + Qwen3-VL-8B (视觉/看图)**. Qwen2.5-7B (SiliconFlow free) for distillation/light tasks.
> HY3 remains conversational base; NOT used for the review chain. Older "HY3→GLM→DeepSeek" chain and GLM-as-primary content below is OBSOLETE — do not revive GLM for review.
> Per-model quirks living doc: `/data/vault/knowledge/VAULT/模型作用心得.md` (3046). Update after each multi-model session.
>
> ⚠️ **历史注记，已被 2026-09-17 实测取代**：现役池已重新纳入 GLM-5.2（`glm-5.2`，直连 open.bigmodel.cn），Kimi 现役模型为 `kimi-k2.7-code`（非 `kimi-k2.6`）。保留此段仅为记录演进，勿据此调用。
### 历史注记 ｜ B ｜ 2026-08-24 STATUS UPDATE (this session's live audit)
> Ran a real 3-model audit on evo_events.py trajectory code. Findings (detail in `references/model-endpoint-quirks.md`；原 `provider-quirks-2026-08-24.md` 已并入）:
> - **Kimi `kimi-k2.6` returned EMPTY every call** → root cause: only 3 models exist now (`kimi-k3`/`kimi-k2.6`/`kimi-k2.7-code-highspeed`), **all force `temperature=1` AND RPM=3 rate-limit** (429→empty). Not a model bug; endpoint is rate-limited to empty. **Kimi is NOT a reliable real-time 二审** — when rate-limited, do NOT fabricate its opinion; use DeepSeek主审 + agent self-verify and note "Kimi unavailable, not adopted".
> - **LongCat-2.0** also returned empty (both content+reasoning) on one call this session. Don't treat a single LongCat empty as "done".
> - **DeepSeek `deepseek-chat` = the stable, complete responder** — caught 4 real bugs (concurrency lock, stats undercount, ms timestamps, token_est method). Keep as audit anchor.
> - **Verify, don't trust single model** still holds; this session LongCat/Kimi both failed partly, only DeepSeek delivered — cross-model redundancy proved its worth.
>
> ⚠️ **历史注记**：其中的模型名（kimi-k2.6）与阵容已被 2026-09-17 实测更新，保留原话以备追溯。
### B ｜ 2026-08-23 实测: LongCat-2.0 / Kimi / Qwen3-VL 关键特性 (务必记牢, 否则踩坑空转)
- **LongCat-2.0 (api.longcat.chat/openai/v1, model=LongCat-2.0)**:
  - 输出在 **`reasoning_content` 字段, 不是标准 `content`**。取响应务必 `ch.get("content") or ch.get("reasoning_content")`，否则拿到空串→误判失败→空转重试。
  - **纯文本, 不能看图** (vision 任务返回"看不到图片")。看图一律走 Qwen3-VL。
  - **会编造**: 推理模型通病, 曾凭语境补全"单价1.52/1.65偏离"但卡里根本无逐行单价。**任何 LongCat 输出必须用代码/实测核验才敢信**。
  - 能发标准 `tool_calls` (agent 编排可用)。先复述任务再分析, 废话多, 取结论段需截断。
  - 1M 上下文是真强项: 整批吞 26 张物料卡做跨卡交叉分析, 揪出逐卡看不出的错乱 (DeepSeek/Kimi 单批吃不下)。
- **Kimi K2.6 (api.moonshot.cn/v1, model=kimi-k2.6)**: 返回结构也可能用 `reasoning_content`, 取字段同样双字段兜底。本场当代码二审。（现役模型名已更新为 `kimi-k2.7-code`，见上"当前可用 key"。）
- **Qwen3-VL-8B-Instruct (api.siliconflow.cn/v1, model=`Qwen/Qwen3-VL-8B-Instruct`)**:
  - ✅ 能看图, 中文图片描述准确自然。单张图占 ~15500 prompt token → 全量烧钱(6481张≈1亿token), **必须抽样**。
  - ⚠ 模型名必须带 `Qwen/` 前缀且用 **Qwen3-VL 系列**; `Qwen/Qwen2-VL-7B-Instruct` 在硅基已不存在 (报 "Model does not exist")。硅基视觉列表: Qwen3-VL-8B/32B-Instruct, Qwen3-Omni 等。
  - 取响应同样 `content or reasoning_content`。
- **通用铁律 (本场印证)**: 推理/视觉模型输出**绝不轻信**, 模型说"X偏离/异常"先写代码核验 (本次 longcat 编造被代码推翻)。这也是用户"核查铁律"的延伸。
- 详见 `references/longcat_qwen_vision_quirks.md`。
