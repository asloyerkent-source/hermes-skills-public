# Aider 与 Codex（安装、后端、坑）

> 来源：合并 `pi-coding-agent` 的 Aider 段 + `coding-agent-tooling` 的 aider 段 +
> `external-model-coding` 的 aider 后端段 + `pi-delegation` 的 Codex 段（2026-09-26）。

---

# Aider

## 定位

**Pi 写新代码，Aider 改已有代码/重构/结对编程。** Aider 用 diff/edit 格式精准改文件，
**不膨胀上下文**，适合"给文件+任务，一次改完"的精准编辑。

## 安装

```bash
pip install aider-install && aider-install
# 或
pip install aider-chat        # 注意包名是 aider-chat，不是同名空壳 aider！
```

- 装错成 `aider`（PyPI 空壳包）会**没有 `aider.exe` 入口**。
- 3046 实测：由 `uv tool` 安装，`~/.local/bin/aider`，版本 **0.86.2**。

## 后端配置（2026-09-26 更新）

> ⚠️ **z.ai / GLM 付费档额度已用尽**：`glm-5.2` / `glm-4.6` 返回 429「余额不足或无可用资源包」。
> 免费档 `glm-4-flash` 仍可用（仅短输出）。原 `zai/glm-4.7-flash` 路线暂不可用。

**3046（Linux）当前配置**——写在 `~/.aider.conf.yml`：

```yaml
model: deepseek/deepseek-chat
read:
  - "$HOME/CONVENTIONS.md"
```

- `DEEPSEEK_API_KEY` 已在 `~/.bashrc` 导出，aider 直接读环境变量，**不需写进配置**。
- **不再需要每次传 `--model`**：`aider --yes --message "<task>" <file>` 即可。
- 实测成本：小任务 **$0.00085**（2.9k 输入 / 106 输出）。
- 切换后端：改 `model:` 一行。备选 `dashscope/qwen3.7-plus`（需 DASHSCOPE_API_KEY）。

## 用法要点

- 非交互：`aider --yes --message "task" <file>`（`--yes` 跳过交互确认）
- **Aider 要求先 add 文件到 chat 才能编辑**，直接给绝对路径不行。
- **超时**：non-terminal 环境容易超时（300s），复杂任务用 `background=true`。
- 任务用 `--message` 传（中文放 bat 里，别 bash `-c` 传，会拆成文件名）。
- 模型名拼写：`deepseek/deepseek-chat`（不是 `deepskip-chat`）。

## ⚠️ Windows/MSYS 坑（仅 Windows 主机适用）

- MSYS 下报 `prompt toolkit: Found xterm-256color, expecting Windows console` → **必炸**。
- **修法**：必须走 `cmd.exe /c xxx.bat` 包装运行（bat 里设好 API key 再调 `aider.exe`）。
- 模板：`references/aider_windows_template.md`（Windows 侧）、
  `references/aider_glm_template.bat`（旧 GLM 版，已落 `H:/HermesShare/aider_fix.bat`）。
- 老配置用 `--model zai/glm-4.7-flash` + 环境变量 **`ZAI_API_KEY`**
  （aider 内置 z.ai provider 认 `ZAI_API_KEY`，不认 `GLM_API_KEY`）。

> 3046 是 Linux，上述 MSYS 坑不适用。

---

# Codex

## 当前状态（2026-09-16 更新，3046）

`codex-cli` v0.154.0：
- ✅ 模型通了（DeepSeek via config.toml）
- ✅ **sandbox 已修复**
- ✅ 文件 I/O 正常

## sandbox 修复（Ubuntu 24.04）

**根因**：Ubuntu 24.04 默认 AppArmor 配置阻止 bwrap 创建 user namespace。

```bash
sudo tee /etc/apparmor.d/bwrap << 'EOF'
abi <abi/4.0>,
include <tunables/global>

profile bwrap /usr/bin/bwrap flags=(unconfined) {
  userns,
  include if exists <local/bwrap>
}
EOF
sudo apparmor_parser -r /etc/apparmor.d/bwrap
```

**验证**：
```bash
sudo aa-status | grep bwrap
bwrap --dev-bind / / --unshare-net echo ok
codex exec --skip-git-repo-check 'say ok'
```

## 调用模板（多文件/复杂工件）

```bash
cd <目标文件的父目录>   # --sandbox workspace-write 只允许写 cwd 树下
timeout 900 codex exec --skip-git-repo-check -m <model> -c model_provider=<provider> \
  --sandbox workspace-write "Read <BRIEF 绝对路径> and implement it exactly. \
Edit only <允许的目录>. Run the compile/selftest commands in the brief and paste \
their real output. Report FILES/SELFTEST/DIFF/DEVIATIONS/UNCERTAINTIES." 2>&1 | tail -60
```

- **显式传 `-m` 与 `-c model_provider=…`**，不要依赖 `~/.codex/config.toml` 的默认模型
  （默认项可能指向已下线的免费模型，一跑就失败）。
- 长任务用 `background=true, notify=true`；前台 `timeout=180` 不够。
- **先把规格写进 BRIEF 文件再让 agent 读**：prompt 只写一句指向，既避 prompt 扫描误拦，
  也能把「已验证的事实」喂全（省掉它自己去调研的十几分钟）。

## Codex vs Pi 分工

| 场景 | 派谁 |
|------|------|
| 简单脚本/配置/文件操作 | Pi |
| 复杂代码/架构/需要深度推理 | Codex（DeepSeek） |
| 写 skill / 改 md / 改 config | Codex（格式规范、注释完整） |
| 超长上下文/隔离执行 | delegate_task 子 agent |

**纪律**：
- Pi 写 md → 用 bash heredoc，不用 write_file（pi-lens 会污染 markdown）
- Codex → 设 `notify=["done"]`，不要无声后台
- 无论谁做 → 独立验证（grep / head / wc）
