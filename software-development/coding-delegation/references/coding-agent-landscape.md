# Coding Agent 生态调研（2026-09-03）

## 已安装

| 工具 | 路径 | 用途 | 状态 |
|------|------|------|------|
| **Pi** | `$HOME/.local/bin/pi` | 短平快写码/配置/文件，模型无关 | ✅ |
| **Aider** | `$HOME/.local/bin/aider` | 结对编程/改代码/重构，接 DeepSeek | ✅ `0.86.2` |

## 已评估 · 待安装

| 工具 | Stars | 协议 | 适合场景 | 成本 | 推荐理由 |
|------|-------|------|----------|------|----------|
| **Aider** | 41.6K | Apache 2.0 | 结对编程、改代码、重构、模型无关 | 低（接 LongCat 免费） | 最对口日常开发，和 Pi 互补（Pi 写新，Aider 改旧） |
| **OpenHands** | 活跃 | 开源 | 完整平台，沙箱隔离，多 agent 编排 | 中 | 重但全，适合危险操作需隔离的场景 |
| **AutoCodeRover** | 活跃 | 开源 | 自动修 GitHub issue，成本极低 | 极低（$0.43/任务） | 学术级，适合批量 issue 修复 |
| **DeepAgents Code** (LangChain) | 活跃 | 开源 | 类 Claude Code CLI，模型无关 | 中 | LangChain 生态，社区活跃 |

## 评估标准

推荐新 coding agent 时按以下维度打分：
1. **模型无关性**：能否接 LongCat 免费额度（不烧钱）
2. **与 Pi 的互补性**：是否覆盖 Pi 不擅长的场景
3. **安装复杂度**：pip install 还是需要 Docker/Node
4. **Hermes 集成度**：是否有现成 skill 或 easy to wrap
5. **沙箱隔离**：危险操作是否需要隔离执行

## 安装决策记录

| 日期 | 工具 | 决策 | 原因 |
|------|------|------|------|
| 2026-09-03 | Aider | ✅ 已装 | 用户同意，接 DeepSeek 作后备 |
| 2026-09-03 | Pi + DeepSeek | ✅ 已配 | Hermes 挂了 Pi 独立可用 |
