# 各执行体能写什么（预检用）

> 派活或跑工具前先确认：**这个执行者能写这个目标吗？**
> 不能写时，报错往往长得像权限问题，实际是设计边界——修法完全不同。

---

## 判断方法：先分清沙箱 vs 真权限

出现 `Read-only file system (os error 30)` 时，**先从沙箱外面测一次同样的写操作**：

```bash
touch <目标目录>/.wtest && rm <目标目录>/.wtest && echo WRITABLE
mount | grep <目标目录>     # 有 ro 挂载吗
```

- 外面**可写**、里面**只读** → **是沙箱策略**，不是权限配错。换执行者或换目标位置。
- 外面也**只读** → 真的挂载/权限问题，去修挂载。

别对“只读”报警直接得出“这个工具坏了”——先分辨清楚再下结论。

---

## Codex CLI

### 沙箱只覆盖 cwd 树下
`--sandbox workspace-write` 允许写的范围是**当前工作目录的树**。目标在 cwd 外面就写不进去。

**修法**：`cd` 到目标的**上级目录**再派。
目标在 `/home/<user>/.hermes/...` 就 `cd /home/<user>`，目标在 `~/.pi/...` 也一样。

### 改不了自己的配置（自我保护）
Codex 的沙箱会把自己的 `$CODEX_HOME`（`~/.codex/`）设为**只读**——目的是不让它运行的
agent 改自己的配置。因此**从 Codex 内部改 `~/.codex/config.toml` 会被挡，换 cwd 无效**。

嵌套调用 `codex exec` 也会因此启动失败（`failed to initialize in-process app-server client:
Read-only file system`）——这是沙箱导致的，**不代表 codex 安装坏了**。

**修法**：改 Codex 自身配置（默认模型、provider、trust）派 **Pi**。

### 长任务
`background=true, notify=true`；前台 `timeout=180` 不够。

---

## Pi CLI

### `~/.pi/agent/.env` 不会被自动加载
Pi **不自动加载** `~/.pi/agent/.env` 去做 `models.json` 里的 `$VAR` 展开。
后果：`apiKey` 写成 `$DEEPSEEK_API_KEY` 的 provider，**变量没导出时会被整个丢弃**——
不是报错，是**静默消失**。

**症状（认这两个就够了）**：

```
Warning: No models match pattern "deepseek/deepseek-chat"
# 且 pi --list-models 里根本没有这个 provider
```

**修法**（任选）：

```bash
# ① 调用前显式导出（推荐）
export DEEPSEEK_API_KEY=$(grep '^DEEPSEEK_API_KEY=' ~/.hermes/.env | cut -d= -f2-)
export KIMI_API_KEY=$(grep '^KIMI_API_KEY=' ~/.hermes/.env | cut -d= -f2-)

# ② 或在 models.json 里直接写内联值（能加载，但 key 落盘）
```

**验证方式**：导出前后各跑一次 `pi --list-models`，对比 provider 数量。
导出后多出来的 provider，就是之前静默丢掉的。

### `enabledModels` 指向不存在的模型 ID
`settings.json` 的 `enabledModels` 里列了 `models.json` 中不存在的 ID → 启动刷屏 warning。
修：只列真实存在的 `<provider>/<model>`，或者删掉这一项。

### 扩展加载失败会让 Pi 完全拒绝启动
症状（不是 warning，是直接退出）：

```
Error: Failed to load extension "<path>/xxx.ts":
Tool "..." registered by extension "..." must define an object parameter schema.
Hint: Start without extensions using "pi -ne".
```

**隔离手法**：用 `pi -ne` 跳过全部扩展对比。`-ne` 能跑 → 就是某个扩展的错，不是 Pi 本体。

**⚠️ 别指望“重新生成扩展”自动修好**：这类扩展常由第三方工具（MCP 客户端等）
按旧版 schema 生成；工具自身版本升了，生成物也未必跟上导致的新校验要求。
重新生成后如果报错一模一样，就该考虑**接管该文件**（删掉自动生成的标记段，自己维护）
或**移除该扩展**——而不是反复重装。

### 调用前确保 PATH 包含 `~/.local/bin`
```bash
export PATH="$HOME/.local/bin:$PATH"
```
否则 `pi: command not found`。

---

## 通用：改了别人的配置后

不管哪个执行体改完，回来都要**独立复验**：

- 解析一遍（`yaml.safe_load` / `json.load`）确认语法没坏；
- 对比改动前后（用 `scripts/config_damage_diff.py`）确认没有意外回退；
- 真跑一次端到端（不带任何参数，走默认路径）——这才是“默认值改对了”的证据。
