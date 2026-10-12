# 工具选型与成本

> 来源：合并 `coding-agent-tooling` + `external-model-coding` 的选型与成本段（2026-09-26）。

## 工具对比（实测）

| 工具 | 成本 | 何时用 |
|---|---|---|
| **Pi** | 免费档≈0（如 LongCat）| 写新代码/配置/文件；短平快任务 |
| **aider + DeepSeek** | 实测 $0.00085/小任务 | **改已有代码/精准编辑**（首选） |
| **aider + GLM** | 免费档≈0 | ⚠️ z.ai 付费档欠费，仅 glm-4-flash 可用 |
| **dsh**（DeepSeek Harness） | agent 多轮→输出爆炸，0.5~1.5 元/次 | 复杂多步自主任务（贵，谨慎） |
| **Codex** | DeepSeek 付费 | 复杂代码/深度推理/多文件工件 |
| **GLM/DS API 直调** | 极低 | 只生成独立**片段**，不碰仓库 |

## DS 成本真相（2026-08 反推自真实账单）

- 输入未命中 **1.04 元/M**，命中缓存 **0.10 元/M**
- **输出 10.30 元/M（暴涨 5.2 倍，旧价 2 元）** ← **贵在这里**
- dsh 单次：保守 0.5 元，多轮膨胀可 1.5 元

**铁律：花费估算不可信，以真实账单为准。**
曾估 0.04 元实际 0.67 元（agent 循环反复塞上下文）。

详见 `references/ds_cost_math.md`。

## dsh 用法（验证过）

- 装：`pnpm install` + `pnpm run build`（需 Node 22+，pnpm 11+）
- 跑：`export DEEPSEEK_API_KEY=<from .env>` 再 `pnpm dsh --profile headless "task"`
- `dsh web` 常驻 127.0.0.1:3080（background 起）
- ⚠️ **dsh 读自己的 credentials，不读 Hermes 的 .env** → 必须显式 export key

## 选型纪律

- 日常小改/精准编辑 → **aider + DeepSeek**（z.ai 额度用尽后已从 GLM 切换）
- 复杂多步自主任务 → dsh（贵，谨慎用）
- **绝不用 dsh 干日常小改**（输出爆炸烧钱）
- 只需生成代码片段（不走整仓编辑）→ 直接调 `references/api-recipes.py`

## agent 生成的代码必须拿真实环境验证（实例）

 dsh 初版给 tele 巡检加"探 8642/8899/9119 三个 /health"，但真实只有 8642 有 /health
（8899=000，9119=302）→ 每轮误判通道死、反复重启网关（假自愈循环）。
GLM + DS 独立审都指出；用真实 `curl` 探测确认必误杀。

**教训：agent 生成的代码必须拿真实环境事实验证，不能信它自述完成。
先 curl/netstat 实测端口，再判逻辑。**

## GLM 超时修复（2026-09-17 实测）

GLM-5.2 推理速度慢，Pi 调用时容易超时：

| 测试条件 | 耗时 | 状态 |
|---------|------|------|
| max_tokens=50 | 2.4s | ✅ |
| max_tokens=200 | 4.9s | ✅ |
| max_tokens=500 | 11.9s | ⚠️ 接近超时 |
| Pi 多轮推理 | >3 分钟 | ❌ 超时 |

**修法**：在 `~/.pi/agent/models.json` 中给 GLM 设 `max_tokens: 150`，强制短输出，5 秒内返回。

**使用策略**：GLM 只做轻任务（<100 字回答、简单分类）；深度推理走 DeepSeek 或 Qwen；
长任务（跨文件重构、项目规划）给 Codex，不要给 Pi+GLM。
