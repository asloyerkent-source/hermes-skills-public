# QQ Bot Setup on Hermes Gateway (3046)

## 快速配置流程

1. **读官方文档**（本地有）：
   ```bash
   cat $HOME/hermes-agent/website/docs/user-guide/messaging/qqbot.md
   ```

2. **凭据**（用户从 q.qq.com 获取）：
   - `QQ_APP_ID=xxx`
   - `QQ_CLIENT_SECRET=xxx`

3. **环境变量**（`~/.hermes/.env`）：
   ```bash
   QQ_APP_ID=xxx
   QQ_CLIENT_SECRET=xxx
   QQ_ALLOW_ALL_USERS=true
   ```

4. **config.yaml** 加 `platforms.qqbot` 块：
   ```yaml
   platforms:
     qqbot:
       enabled: true
       extra:
         app_id: "xxx"
         client_secret: "xxx"
         dm_policy: open
         group_policy: disabled
   ```

5. **关键坑**：.env 改完不等于 systemd service 能读到，必须显式 import：
   ```bash
   source ~/.hermes/.env
   export QQ_ALLOW_ALL_USERS QQ_APP_ID QQ_CLIENT_SECRET
   systemctl --user import-environment QQ_ALLOW_ALL_USERS QQ_APP_ID QQ_CLIENT_SECRET
   systemctl --user restart hermes-gateway
   ```

6. **验证**：
   ```bash
   tail -10 ~/.hermes/logs/gateway.log | grep -iE "qqbot|error"
   # 期望看到：[QQBot:xxx] Connected
   # 错误：invalid appid or secret → 凭据错
   # 错误：open policy without allow-all → 缺 QQ_ALLOW_ALL_USERS
   ```

## 2026-09-02 实际配置

- App ID: `1905548201`
- App Secret: `<REDACTED - 见 ~/.hermes/.env 或本地凭据册>`
- 状态：✅ 连通（WebSocket 已连，Ready session_id=7d3b3e33）
- 旧 Secret `4014001803` 是错的，QQ 平台返回 code=100016 `invalid appid or secret`

## 2026-09-03 补充：config.yaml extra 块优先级坑

Gateway 读取 QQ Bot 凭据的优先级：**config.yaml `platforms.qqbot.extra` > .env**

如果 config.yaml 里 extra 块的 `client_secret` 是错的（如旧值 `4014001803`），即使 .env 里是正确的 `<REDACTED - 见 ~/.hermes/.env 或本地凭据册>`，gateway 也会认证失败。

**修法**：用 `hermes config set platforms.qqbot.extra.client_secret '正确值'` 修正。

## 验证命令

```bash
# Gateway 是否运行
pgrep -f "hermes_cli.main gateway run"

# QQ Bot 是否连接
grep -i qqbot ~/.hermes/logs/gateway.log | tail -5

# 系统变量是否导入
systemctl --user show-environment | grep -i qq
```


---
# mihomo 微信代理修复

# 微信 Bot "proxy error 400" 完整排查与修复

## 问题现象
微信 bot 回复 "proxy error 400"。

## 错误链路（实际）
1. 微信收到消息 ✅
2. 网关调 LLM 生成回复 → 走全局 `proxy_url: http://127.0.0.1:7890`（mihomo）❌
3. mihomo 对 `api.longcat.chat` 返回 400
4. 网关回复 "proxy error 400" 给用户

## 根因
**config.yaml 第160行有全局 `proxy_url`**，所有 LLM API 请求都推给 mihomo。LongCat 是国内服务，不需要代理。

## 修复方法
删除 config.yaml 顶层全局 `proxy_url`，只保留 `platforms.telegram` 下的 proxy_url。

```yaml
# 删除这一行（顶层）
proxy_url: http://127.0.0.1:7890

# 保留这一行（telegram 平台内）
platforms:
  telegram:
    proxy_url: http://127.0.0.1:7890
```

## 验证
```bash
# 确认只剩 telegram 一处
grep -n proxy_url $HOME/.hermes/config.yaml

# 确认 gateway 环境变量无 HTTP_PROXY
PID=$(pgrep -f "hermes_cli.main gateway run" | head -1)
tr "\0" "\n" < /proc/$PID/environ | grep -i proxy
# 应该只有 TELEGRAM_PROXY，没有 HTTP_PROXY / HTTPS_PROXY
```

## 排查过程中的错误理论（不要重复）
### ❌ 理论1：mihomo 路由规则缺少 weixin.qq.com DIRECT
- 在 mihomo 配置里加了 `DOMAIN-SUFFIX,weixin.qq.com,DIRECT`
- curl 验证从 400 → 404，看似有效
- **但微信仍然回复 400**，因为问题不在 iLink API 本身

### ❌ 理论2：gateway 进程环境变量 HTTP_PROXY 导致
- 改了 .bashrc / .env / systemd service / /etc/environment
- 全都没用，因为根因是 config.yaml 的全局 proxy_url，不是环境变量

## 关键教训
1. **先读官方文档/源码**：官方文档明确说微信用 long-poll，源码里 `trust_env=True` 说明走环境变量。如果一开始就读源码，不会瞎试
2. **先多模型分析再动手**：用户明确要求"多模型分析一下，然后用pi去动手"，不要自己瞎试
3. **日志里的 api_calls=0 是关键线索**：说明 LLM API 调用根本没成功，不是微信 API 的问题
4. **Pi 写脚本 + Hermes 验证**：Pi 写 bash 脚本，Hermes 读真文件确认内容 + 真跑命令验证结果

## 相关文件
- `$HOME/.hermes/config.yaml` — Hermes 主配置
- `$HOME/mihomo_config.yaml` — mihomo 代理配置
- `$HOME/hermes-agent/gateway/run.py:29828` — "Proxy error" 日志输出位置
- `$HOME/hermes-agent/gateway/platforms/weixin.py:1321` — `trust_env=True` 源码位置


---
# TokenTracker 监控

# TokenTracker 监控体系配置（2026-09-12 落地）

## 架构

```
Hermes state.db ──┐
                   ├──→ TokenTracker (JSONL) ──→ 日报脚本 ──→ cron 投递
Pi session JSONL ─┘```

## 文件

| 文件 | 用途 |
|------|------|
| `~/.hermes/scripts/token_report.py` | 日报 + 月报（daily / monthly） |
| `~/.hermes/scripts/token_report_weekly.py` | 周报（weekly） |
| `~/.tokentracker/tracker/queue.jsonl` | TokenTracker 原始数据 |
| `~/.hermes/cron/output/token_daily_*.md` | 日报输出 |
| `~/.hermes/cron/output/token_weekly_*.md` | 周报输出 |

## Cron

| 任务 | 时间 | 投递 |
|------|------|------|
| token日报 | 每天 06:10 | origin |
| token周报 | 周一 06:20 | origin |
| token月报 | 月1号 06:30 | origin |

## 日报格式（v2）

```markdown
📊 Token 消耗日报 (YYYY-MM-DD)
==================================================
数据来源: TokenTracker (本地JSONL)
对账来源: Hermes state.db

📅 每日明细
--------------------------------------------------
📆 YYYY-MM-DD
  会话数: N
  ├─ 新 tokens: N
  │  ├─ 输入: N
  │  ├─ 输出: N
  │  └─ 推理: N
  ├─ 缓存命中: N (XX%)
  ├─ 费用: $X.XXXX
  └─ TokenTracker 总量: N (含缓存)
  模型分布:
    - model: N (缓存 N, N 会话)
  🔄 Hermes 对账: N (N 主会话, $X.XXXX)
```

## 对账规则

1. **新 tokens** = input_tokens + output_tokens + reasoning_output_tokens（不含缓存命中）
2. **缓存命中** = cached_input_tokens（单独列出，不算消耗）
3. **总费用** = total_cost_usd（从 API usage 记录）
4. **异常检测**：
   - 新 tokens > 50M/天 → ⚠️ 告警
   - TokenTracker / Hermes < 0.5 或 > 3.0 → 🔴 可能漏采或重复计数

## 已知陷阱

| 陷阱 | 影响 | 解决 |
|------|------|------|
| state.db 无 total_tokens 列 | 查询报错 | 用 input_tokens + output_tokens + reasoning_tokens |
| state.db 时间列名 | 报错 | 用 started_at（不是 created_at） |
| TokenTracker total_tokens 含缓存 | 数值虚高 10x+ | 看 new_tokens 字段 |
| npm allow-remote=none | pi-mcp-adapter 装不上 | `npm config set allow-remote all --location user` |
| Pi 改 config.yaml 覆盖 Hermes 修改 | 配置回退 | 配置文件归 Pi 管，Hermes 只读不改 |
| device_token 缺失 | 远程同步不可用 | `tokentracker device-login` 获取6位码 → 浏览器 www.tokentracker.cc/device 授权（⚠️ `init --link-code` 只是本地初始化，不绑定设备，远程 dashboard 永远看不到数据） |
