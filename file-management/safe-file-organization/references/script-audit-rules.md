# 用户自建脚本审计与清理 — 原技能 `script-audit-cleanup` 正文（逐字）

> 2026-09-27 「文件整理簇」4→1 合并：本文件逐字并入源技能 `script-audit-cleanup/SKILL.md` 的正文（去 frontmatter）。
> 源目录已归档于 `.archive/script-audit-cleanup/`，原件逐字保留；备份 `~/.hermes/skill-backups/merge-cleanup-20260927-001231/`。

# 脚本审计与清理

## 触发场景
用户要求清理无用脚本、审计项目、全面审查编程项目、找出会跑偏/失效脚本，或抱怨"脚本太多没用"。

## 致命陷阱（已踩坑，必读）
`hermes-agent/` 下 3900+ 个 .py 是 Hermes **软件本体**（包/tests/plugins），不是用户写的，绝对不能清。
它们靠 Python `import` 关联，非文件名引用 → 用"文件名互搜"判定会把全部误判成孤儿。
首次审计若全量扫描会列出 `hermes_cli/*` `acp_adapter/*` `tests/*` `plugins/*` 为"可删"——**错，会删崩赫米**。

## 正确审计范围（硬规则）
排除目录：`hermes-agent`、`acvenv2`、`node_modules`、`ds_harness`、`site-packages`、`.git`、`venv`、`__pycache__`、`_trash_*`、`skills`、`optional-skills`
用户自建根目录：`H:/HermesShare`、`H:/K50backup`、`H:/HermesServe`、`H:/Hermes`、`.../hermes/scripts`、以及 `.../hermes/` 根层散落文件（**不递归进 hermes-agent**）

> 真实范围：用户自建脚本约 182 个，孤儿通常个位数（ROM 残留/过时bat/被取代的一次性脚本）。

## 执行流程
1. 收集 `.py`/`.bat`（按范围 walk）
2. 引用分析：文件名互搜 + `schtasks /query /fo LIST /v` dump 后本地 grep 任务计划引用
3. 孤儿判定：无文件引用 + 未被任务计划调用 + 修改 >7天
4. 读真实代码分类：🔴写死旧网段(31.x)/旧PID失效 🟡被取代/空壳/一次性demo 🟢仍属某体系资产→保留
5. 清理：移到 `_trash_YYYYMMDD/` 备份（**不永久删**，可反悔），不自动 rm
6. 绝不自动删用户文件；删除需用户拍板

## Pitfall
- schtasks 逐任务 `/xml` 慢(超时) → 用 `/fo LIST /v > dump.txt` 一次 dump 再 grep
- MSYS 下 `$HERMES_HOME` 可能不展开 → 用真实路径 `C:/Users/<user>/...`
- 中文 `-c` 参数 exit 49 → 写 .py 文件执行
- 扫 4000+ 做 O(n²) 匹配会超时 → 限定范围别全量

## 常见"会跑偏"真实 bug
- 写死 PID：watchdog `PIDFILE=12345` 旧进程号，任务完仍空转误报
- 写死旧网段：`192.168.99.X` 内网已改 2.x，连错
- 功能重叠守护：gateway_guard+infra_selfcheck+proxy_watchdog 三套探网关/代理→重复+半成品
- 直连外网受代理：探 api.telegram.org 受 Clash 抖假报"出网断"→改探本机 8642/health(--noproxy)

## 验证
清理后确认 trash 文件数、原位置已空；月度审计 cron 正常态零输出，仅新孤儿才报告且不删。


---

## 附：源技能 frontmatter（逐字存档）

```yaml
name: script-audit-cleanup
description: 审计清理用户自建脚本。触发于"清理无用脚本/审计项目/全面审查编程项目"。必排除 hermes-agent 软件本体。
```


---

# 从主 SKILL.md 拆出（2026-09-27 文件整理簇合并，逐字）

**常见"会跑偏"真实 bug**：写死 PID（watchdog `PIDFILE=12345` 旧进程号，任务完仍空转误报）；写死旧网段（`192.168.99.X` 内网已改 2.x，连错）；功能重叠守护（gateway_guard+infra_selfcheck+proxy_watchdog 三套探网关/代理 → 重复+半成品）;直连外网受代理（探 api.telegram.org 受 Clash 抖假报"出网断" → 改探本机 8642/health `--noproxy`）。


---

# 从主 SKILL.md 拆出（2026-09-27 文件整理簇合并，逐字）

### 正确审计范围（硬规则）
**排除目录**：`hermes-agent`、`acvenv2`、`node_modules`、`ds_harness`、`site-packages`、`.git`、`venv`、`__pycache__`、`_trash_*`、`skills`、`optional-skills`
**用户自建根目录**：`H:/HermesShare`、`H:/K50backup`、`H:/HermesServe`、`H:/Hermes`、`.../hermes/scripts`、以及 `.../hermes/` 根层散落文件（**不递归进 hermes-agent**）

> 真实范围：用户自建脚本约 **182 个**，孤儿通常**个位数**（ROM 残留 / 过时 bat / 被取代的一次性脚本）。

**流程**：① 按范围 walk 收集 `.py`/`.bat` → ② 引用分析（文件名互搜 + `schtasks /query /fo LIST /v` dump 后本地 grep 任务计划引用）→
③ 孤儿判定（无文件引用 + 未被任务计划调用 + 修改 >7 天）→ ④ **读真实代码分类**：🔴写死旧网段(31.x)/旧 PID 失效 🟡被取代/空壳/一次性 demo 🟢仍属某体系资产→保留 →
⑤ 清理：移到 `_trash_YYYYMMDD/` 备份（**不永久删，可反悔**），不自动 `rm` → ⑥ **绝不自动删用户文件；删除需用户拍板**。

**Pitfall**：`schtasks` 逐任务 `/xml` 慢（超时）→ 用 `/fo LIST /v > dump.txt` 一次 dump 再 grep；MSYS 下 `$HERMES_HOME` 可能不展开 → 用真实路径 `C:/Users/<user>/...`；中文 `-c` 参数 exit 49 → 写 .py 文件执行；扫 4000+ 做 O(n²) 匹配会超时 → 限定范围别全量。
