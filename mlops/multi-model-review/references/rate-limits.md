# GLM / DeepSeek 免费档限流实测（2026-08-14）

## 智谱 GLM（open.bigmodel.cn — 非 api.z.ai）
- **正确端点**: `https://open.bigmodel.cn/api/paas/v4/chat/completions` (2026-08-16 验证通; api.z.ai 实测 404/SSL EOF 不可用, 勿用)
- 免费档 RPM 极低，刚注册权益等级低，几分钟即 429 (错误码1302 用户速率限制)
- 高峰动态限流 + 平台级过载(1305) 都可能导致空回
- 长输出（>400字）常被截断为**空 content**（reasoning 占满预算，content 截到 length）
- **读取务必 content or reasoning_content** (免费档正文常在 reasoning_content, 只读 content 拿空串→空重试→超时)
- 模型：glm-4.5-air / glm-4.7-flash（flash 输出能力受限更易空回）
- 应对：短输出(200-1000tok) + 退避重试(12-20s×5-8) + 长任务放低峰(03:00) + 失败不计费不硬耗
- **免费额度仅 3 个月** → 优先用, 一旦失联/失败立即切 SiliconFlow (见下)

## DeepSeek（api.deepseek.com）
- **用户充值 key（付费，非免费档）**：走 `https://api.deepseek.com/v1`，账单用户的 DeepSeek 余额
- deepseek-v4-flash 直连，国内API应 `proxies={"http":None}` 绕过 Clash（否则代理抖→SSL断→空回，别误判成限流）
- 偶发空 content 多为代理抖/瞬截，非 RPM 墙（付费档无免费档那种 RPM 卡死）
- 比 GLM 免费档稳得多；长输出基本能回；用户对此用法满意且便宜

## 用户模型路由纪律（2026-08-19 最终定, 覆盖编程+审查）
- **GLM 优先**: 免费额度仅3个月, 优先用 (端点 open.bigmodel.cn); 一旦失联/失败立即切 SiliconFlow
- **SiliconFlow 兜底**: 用户充值 ¥10 + 注册送 ¥14; 模型 `Qwen/Qwen3.5-35B-A3B` (便宜MoE), 国内直连稳; 仅 GLM 真失败时切
- **DeepSeek 审计**: 直连 api.deepseek.com (付费key), 用户满意且便宜, 用于审核/审计
- **HY3 禁止用于编程** (用户实测 hy3 编程基本没搞好过); 编程走 aider+GLM 零成本 (已验证 2.1k+2.8k token≈0元)
- **Nous 额度禁跑国产模型**: GLM/DS 必须直连官方端点, 不可经 Nous Portal (404+扣额度)
- DSL/豆包等: GLM 免费额度用光再注册切换

## 关键坑
- Nous Portal `inference-api.nousresearch.com/v1` 对 `zai/glm-*` 返回 404 → GLM 走 `open.bigmodel.cn` 直连 (非 api.z.ai, 也404)
- 不要为省事用 Nous Portal 调国产模型（既 404 又扣额度）
- `.env` 里 key 若带引号 (如 `'sk-xxx'`) 会导致 401, 读取时须 strip 首尾引号 (SiliconFlow key 曾因此 401)
