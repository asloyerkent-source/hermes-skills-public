# Pi 的坑（全部实踩过）

> 来源：合并 `pi-delegation` + `pi-coding-agent` + `coding-agent-tooling` 的相关段（2026-09-26）。

## 1. pi-lens 会自动改写 Pi 写的 .md（2026-09-17 实战）

`~/.pi/agent/settings.json` 装了 `npm:pi-lens`，Pi 写 .md 后 markdownlint --fix 会自动重写：
已有 URL 被包尖括号、H1 后插空行、插入空字符。

**铁律**：写 .md / .json / 其他格式化文件前，必须要求 Pi：
- **只 bash heredoc 写**（`cat > file << 'EOF'` 或 `echo >> file`）
- **不用 write_file / edit 工具**
- Pi 改完 .md 后 Hermes 必须 **diff 对比 + grep 验证**（尤其 URL 和 Unicode）
- 派发 prompt 里写明："只 bash heredoc，不用 write_file 工具"

**修法**：从 `~/.pi/agent/settings.json` 的 packages 中移除 `npm:pi-lens`。

## 2. Pi 创建 .env 会覆盖已有文件（2026-09-06 实测，严重）

Pi 用 `cat > $HOME/.hermes/.env << 'EOF'` 创建新 .env，**覆盖了原文件**，
导致 DEEPSEEK_API_KEY、KIMI_API_KEY、GLM_API_KEY、QNAIGC 全部丢失。

**铁律**：
1. 任何涉及 `.env` / `config.yaml` / credentials 的任务，prompt **必须包含"先备份原文件"**：
   `cp ~/.hermes/.env ~/.hermes/.env.bak.$(date +%Y%m%d_%H%M%S)`
2. Pi 创建 .env 必须**追加模式或逐行写入**，不能覆盖模式。
3. Pi 完成后 Hermes 必须 `diff` 对比新旧 .env。
4. "创建配置文件"类任务必须先读原文件内容再修改，不能从空白开始写。

## 3. 范围纪律（2026-08-29 实测翻车）

- **用户说"装 Pi"就是装 Pi**。装完别擅自发散去接 Ollama/配本地算力（用户原话"怎么又扯到 ollama 了"）。
- 模型/provider 那层是**用户自己的事**：他要订阅就用 `/login`，要 API key 他自己设。
- 正确顺序：装 → 验证 `pi --version` → **问用户**要不要配后端/配哪个 → 他指定了再配。

## 4. `-p` prompt 会被两类安全扫描拦（两种独立根因）

**扫描A — Confusable Unicode / homoglyph**
- 触发：prompt 含 em-dash `—`、箭头 `→`、中文引号 `""`、emoji。**纯中文正文也会触发**（不止 emoji）。
- 根因：特殊字符被当"视觉仿 ASCII 攻击"。

**扫描B — Trailing dot in hostname**
- 触发：prompt 里出现 `IP:端口.` 写法（如 `http://127.0.0.1:7890.`），句点紧跟在主机名/端口后。
- 根因：安全正则匹配 `hostname模式后跟点`，被当 FQDN 绝对域名误判。
- **实测**：hexdump 显示 `127.0.0.1:7890.\n`，报错 "Trailing dot or whitespace in hostname"。
  **与 emoji 无关，纯 ASCII 也会中招。**

**统一修法**：
1. prompt **纯 ASCII**（英文 + 半角 `-` `>`），中文需求用英文描述让 Pi 自己理解；
2. **绝不在 `数字:数字` 后加句点**；
3. 不用 emoji / 中文引号 / em-dash / 箭头；
4. 或把 prompt 写文件再 `pi -p "$(cat prompt.txt)"` 隔离终端转义。

> 注意：扫描只拦 **Hermes 的终端命令**，不拦 Pi 写文件（Pi 写中文 skill 正常）。

## 5. 模型幻觉：AI 会编造扩展名/参数（2026-09-12 实踩）

多模型交叉审核（DeepSeek/Kimi/LongCat）仍会编造**听起来真实但不存在**的 Pi 扩展名：
- DeepSeek 编造：`pi-litellm-autorouter`、`pi-bifrost`、`pi-web-access-lean`、
  `@afx-team/pi-mcp-adapter`、`memory-meow`、`memento`、`pi-agents-flow`、
  `pi-agent-extensions`、`@pi-unipi/unipi`、`awesome-pi-coding-agent`、
  `agtop`、`abtop`、`TokenMeter`、`AgentSight`、`OpenLLM Monitor`
- 豆包编造：`pi_encoding` 参数组（`compression_budget`/`flush_interval_turns`、`config.override.yaml`）
- 实测：文章推荐的扩展约 **50% 不存在**，DeepSeek 推荐的 10 个里 **8 个不存在**。

**铁律**：推荐安装前**必在 pi.dev/packages 搜一遍验证真伪**。
多模型一致推荐的也要验证——**全模型一致幻觉并不罕见**，它们会互相"确认"对方的幻觉。
验证标准：pi.dev 搜到 / GitHub 有仓库 / npm 有包，三者都无 = 不存在。

## 6. Pi 的结论不可全信（实测两次打脸）

- **反例1**：Pi 报"Kimi key 失效 401"，实测 direct curl moonshot 活；
  根因是 hermes config 无 kimi provider（非 key 死）。
- **反例2**：Pi 报 wiki 混了 3302 个 `_raw_compiled_*`，实测 `find | wc -l` 只有 2273。
- **反例3**：Pi 审 `device_health_check.sh` 声称 L12 有 bash 优先级 bug（302 时会返回 DOWN）。
  **实测 302 返回的是 UP（正确）**——Pi 把短路逻辑推演反了。

**铁律**：Pi 写的代码 / 审查结论 / bug 定位，**永远实跑验证**再采信或回写 AGENTS.md。
尤其 **bash 逻辑、正则、退出码**这类 Pi 易推演错的。
多模型审中 DeepSeek 主审通过的，可信度高；**Pi 单方面的审查报告按"待验证"处理**。

## 7. Pi 自我保护（2026-09-16 实战）

Pi 会**拒绝执行会中断自己运行的操作**，比如 `mv ~/.pi /data/fast/`。
**这是正确行为——尊重，不要绕过或手动替代。**

- 场景：用户要求移动 Pi 数据目录释放系统盘空间。Pi 拒绝，因为 `~/.pi/` 是它的家目录，
  移动会导致正在运行的进程失去状态、会话中断。
- 解法：① 接受 Pi 的拒绝；② 如需移动 → 先停 Pi → 移动 → 重建符号链接；
  ③ 或保留原位，清缓存子目录释放空间。

## 8. 必须给绝对路径（2026-09-12 实踩）

- Pi 改 config.yaml 可能改到 `$HOME/config.yaml` 而非 `$HOME/.hermes/config.yaml`。
- 任务里必须写**绝对路径**，不能只写 `config.yaml`。
- 派完立即验收：`grep -A10 "^model:" $HOME/.hermes/config.yaml` 确认改对了。

## 9. 配置修改纪律（2026-09-12）

- **Hermes 不亲自改 config.yaml**，所有配置修改必须派 Pi 执行。
- 流程：Hermes 出方案 → Pi 执行（绝对路径）→ Hermes 验收。
- 原因：同时改同一文件会互相覆盖，Pi 的"修复"会覆盖手动配置。
