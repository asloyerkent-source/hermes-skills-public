# Pi Coding Agent（安装与配置）

> 来源：合并 `pi-coding-agent` SKILL.md + `coding-agent-tooling` 的 Pi provider 段（2026-09-26）。

开源编码代理 `earendil-works/pi-coding-agent`（Node CLI，46k+ stars）。纯编码副手：
在代码库里读写改、跑命令。与 Hermes 互补——Pi 干 coding 细活，Hermes 管调度/远程/记忆。

## 安装

- 要求 Node >= 21（实测 3046 为 Node v22，满足）。
- 全局装（不用 sudo，前缀可写）：
  ```bash
  npm install -g --ignore-scripts @earendil-works/pi-coding-agent
  ```
  - `--ignore-scripts` 避免 postinstall 钩子拉多余东西；实测正常。
  - 全局前缀若在 `~/.local`，`pi` 落在 `~/.local/bin/pi`，**调用前 `export PATH="$HOME/.local/bin:$PATH"`**。
- 验证：`pi --version`（实测 0.84.4）。

## 交互与调用

- `pi` 进交互模式；`/login` 选订阅（Claude Pro/Max、ChatGPT Plus/Codex、GitHub Copilot、xAI、OpenRouter），或设 API key 环境变量。
- 非交互跑任务：`pi --provider <p> --model <m> -p "自然语言任务"`
- 列出已配置模型：`pi --list-models`（验证 models.json 被加载的关键命令）

## 配置后端（`~/.pi/agent/models.json`）

若无则 `mkdir -p ~/.pi/agent`。**OpenAI 兼容端点写法**：

```json
{
  "providers": {
    "longcat": {
      "baseUrl": "https://api.longcat.chat/openai/v1",
      "api": "openai-completions",
      "apiKey": "$LONGCAT_API_KEY",
      "authHeader": true,
      "compat": { "supportsDeveloperRole": false }
    }
  }
}
```

- `apiKey` 用 `$ENV_VAR` 引用（**不把 key 明文落盘**）。
- 调用前必须 export：`export LONGCAT_API_KEY=$(grep '^LONGCAT_API_KEY=' ~/.hermes/.env | cut -d= -f2-)`
- 硅基流动：`baseUrl: https://api.siliconflow.cn/v1`
- Ollama 本地：`baseUrl: http://<host>:11434/v1`，`api: openai-completions`
- `pi --list-models` 显示 `provider / model / context / max-out / thinking / images` 列 → 确认加载成功。

## 添加新 Provider（以 Kimi 为例）

```python
import json
path = "$HOME/.pi/agent/models.json"
with open(path) as f: data = json.load(f)
data["providers"]["kimi"] = {
    "baseUrl": "https://api.moonshot.cn/v1",
    "api": "openai-completions",
    "apiKey": "$KIMI_API_KEY",
    "authHeader": True,
    "compat": {"supportsDeveloperRole": False, "supportsReasoningEffort": False},
    "models": [{"id": "kimi-k2.7-code", "name": "Kimi K2.7 Code",
                "contextWindow": 131072, "maxTokens": 8192,
                "cost": {"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0}}]
}
with open(path, "w") as f: json.dump(data, f, indent=2, ensure_ascii=False)
```

运行前：`export KIMI_API_KEY=$(grep KIMI_API_KEY $HOME/.hermes/.env | cut -d= -f2-)`

### DeepSeek Provider
- baseUrl: `https://api.deepseek.com`
- 模型：`deepseek-chat`（V3）、`deepseek-v4-flash`、`deepseek-v4-pro`
- **注意**：DeepSeek 输出单价已涨至 10.30 元/M，按量付费。

## 当前模型配置（2026-09-14 用户终裁）

**DeepSeek 已升为 Pi 首选模型**（LongCat 不再作主模型）：

```bash
# 新建/开发类（首选）
pi --model deepseek/deepseek-chat -p "$(cat /tmp/task_prompt.txt)" /tmp/output.py

# 复杂任务后台跑
pi --model deepseek/deepseek-chat --background -p "$(cat /tmp/task.md)"
```

- DeepSeek 挂了切 Kimi：`kimi-k2.7-code`
- DeepSeek key 已持久化到 `~/.bashrc`，Hermes 挂了 Pi 独立可用。

## 真实验证铁律（别假装"已验证"）

- 配完后端**必须实跑一次**才说可用：
  `pi --provider longcat --model LongCat-2.0 -p "reply with: ok"` → 返回才算通。
- **让 Pi 把产出写到文件**（`-p "write the result to /path/x.py"`）而非只打印，
  否则 `head -N` 截断会丢关键内容（实测审 SSH 脚本时打印版截掉了 255 重试逻辑）。
- 打印长脚本用 `head` 会截断 → 让 Pi 写文件再 `read_file`。
- `-p` 单次任务给足 `timeout`（90s+）。
- `--list-models` 与 `-p` 非交互混用无进度条。
- Node 前缀不在 PATH 时 `pi: command not found` → `export PATH="$HOME/.local/bin:$PATH"`。

## Pi 的定位（红线）

- **不把 Pi 当通用 agent 用**（它只 coding，无记忆/调度）。
- 写代码优先派 **Pi**；调研/读文件/批量杂活派 **通用子 agent**（delegate_task）。
- 关系：用户要 A 就做 A，不擅自发散（装 Pi 别顺手接 Ollama）。
