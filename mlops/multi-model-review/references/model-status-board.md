# 模型状态板（2026-09-17 实测）

多模型交叉审核池的当前可用模型 / 状态 / 价格 / 限制。`references/roster-and-keys.md`「当前可用 key」章节的权威副本。

## 可用模型（五路并行池，总权重 10）

| 模型 | Provider | model | endpoint | keyenv | 权重 | 价格 | 限制 |
|------|----------|-------|----------|--------|------|------|------|
| DeepSeek（主审） | deepseek | `deepseek-chat` | `https://api.deepseek.com/v1` | `DEEPSEEK_API_KEY` | 3 | 付费（峰谷×2：北京 09–12 / 14–18） | 无 |
| GLM-5.2 | glm | `glm-5.2` | `https://open.bigmodel.cn/api/paas/v4` | `GLM_API_KEY` | 2 | 免费额度 / 付费 | 高峰动态限流（错误码 1302/1305） |
| Qwen3.7+ | dashscope | `qwen3.7-plus` | `https://dashscope.aliyuncs.com/compatible-mode/v1` | `DASHSCOPE_API_KEY` | 2 | 百炼免费额度 / 付费 | 无 |
| Kimi | kimi | `kimi-k2.7-code` | `https://api.moonshot.cn/v1` | `KIMI_API_KEY` | 2 | 付费 | **限 3 RPM**；`temperature` 必须=1 |
| LongCat | longcat | `LongCat-2.0` | `https://api.longcat.chat/openai/v1` | `LONGCAT_API_KEY` | 1 | 免费（资源包） | 并发/长跑必 429 |

- 共识标尺 = 10 分（权重和）：≥6 采纳 / 4–5 部分一致（人工复核）/ <4 无共识。
- 铁律：主审必须是 DeepSeek（权重 3）；LongCat 免费但不顶主审。

## 已移除 / 未配置（勿引用）

| 模型 | 状态 | 说明 |
|------|------|------|
| 七牛云聚合层（原多模型聚合） | ❌ billing 暂停（2026-09-17） | 全部聚合端点下线；相关 GPT/Gemini 路由一并失效，改用 Qwen3.7+ (DashScope) |
| HY3 | ⚠️ 免费档已过期 | 付费版仍在，非默认池成员 |
| MiniMax | ❌ 从未配置端点 | `MINIMAX_API_KEY` 缺失，不入池 |
| Nous Sonnet | ❌ 从未使用 | 未配置路由 |
| GPT-4o-mini / Gemini | ❌ 随聚合层下线 | — |

## 备用通道

- LongCat via Nous 平台：`https://inference-api.nousresearch.com/v1`，`meituan/longcat-2.0:free`，`NOUS_API_KEY`（免费，等价备用）。

## 探活

跑 `scripts/model_key_health.sh` 探活；≥3 个返回 200 才 PROCEED（退出码 0）。

## 价格参考（每百万 token，2026-09 实测）

- DeepSeek Flash：官网 ¥3.08/¥9.24；谷值原价、峰值×2。
- GLM-5.2：siliconflow ¥6/¥28；百炼/智谱免费额度优先。
- Qwen3.7+：百炼每模型独立免费额度，超出按官网计价。
- Kimi K2.7 Code：¥6.5/¥27。
- LongCat-2.0：官方免费资源包（到期需续）；siliconflow ¥5/¥20。
