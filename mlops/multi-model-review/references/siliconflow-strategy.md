# SiliconFlow 作为 GLM 兜底的策略与定价（2026-08-19 实测）

## 为什么需要它
GLM 免费额度仅 3 个月 + 免费档 RPM 低易空回。一旦 GLM 失联/失败，需要稳定的国内直连兜底。SiliconFlow 是国内可达的模型聚合 API，用户已充值 ¥10 + 注册送 ¥14。

## 真实定价（元 / 百万 token，查自 siliconflow.cn pricing 2026-08）
- Qwen3.5-9B: 入 ¥0.18 / 出 ¥0.50（轻活近零成本）
- Qwen3.5-35B-A3B (MoE): 约 入 ¥0.1 / 出 ¥0.3（兜底默认选这个）
- Qwen3.5-122B-A10B: 入 ¥0.17 / 出 ¥0.52
- DeepSeek-V3.2: 入 ~¥0.27 / 出 ~¥1.00
- **免费模型层**: Qwen2-7B/1.5B、GLM-4-9B 等调用费 ¥0（干轻活零成本）
- 91+ 模型可用；国内直连延迟 ~0.24s（api.siliconflow.cn）

## 路由纪律（用户 2026-08-19 定）
1. GLM 优先（open.bigmodel.cn，3个月免费白嫖）
2. DeepSeek 审计（api.deepseek.com 付费key，用户满意便宜）
3. **GLM 全失败 → 切 SiliconFlow** Qwen3.5-35B-A3B（不轻易动 ¥10 保底）
4. HY3 禁编程（实测差）；编程走 aider+GLM 零成本，GLM失联切 SF

## 坑
- `.env` 里 `SILICONFLOW_API_KEY='sk-xxx'` 带单引号 → 401。读取须 strip 首尾引号（本次已修）。
- SF 是聚合平台，调法同 OpenAI 格式：`https://api.siliconflow.cn/v1/chat/completions`，模型名带组织前缀（如 `Qwen/Qwen3.5-35B-A3B`）。
- 同样需 `proxies={"http":None}` 绕过 Clash 继承，否则 SSL 抖。

## 额度监控建议
每周查一次 SF 余额（GET /v1/user/info 或 dashboard），低于阈值提醒用户；避免不知不觉烧光 ¥10 保底。
