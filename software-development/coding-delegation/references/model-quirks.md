# 子模型 API 实测怪癖（2026-08-15 验证）

> 来源：从 submodel-codegen 合并而来。可调用代码见 `api_recipes.py`。

## GLM（api.z.ai / open.bigmodel.cn，`GLM_API_KEY`）

| 模型 | 长输出行为 | 判定 |
|---|---|---|
| glm-4.7-flash | HTTP 200 但 `content` **空**（输出 >~1k token） | ❌ 写码不可靠 |
| glm-4.6-flash | HTTP 403（限流 / 免费档封顶） | ❌ 被封 |
| glm-4-flash | 可用，但仅短文本（~100–600 token） | ✅ 短草稿/短评审 |

**实践**：写代码优先用 DeepSeek；glm-4-flash 只用于短评审/片段。

## DeepSeek（api.deepseek.com，`DEEPSEEK_API_KEY`）

- `deepseek-chat` 审查能力强：**一次审出 150 行草稿里 13 个不同 bug**。
- **截断**：`max_tokens` 小于实际长度时代码被**从函数中间切断** → 拼装后 `SyntaxError`/`IndentationError`。150 行脚本需 `max_tokens ~3000`，仍要盯尾部。
- 必须带 `proxies={'http':None,'https':None}` 绕开 Clash（否则该进程不吃 `NO_PROXY`）。

## 装配坑（本次全部踩过）

- 写文件前先剥掉 ```python / ``` 围栏标记。
- 解析器输出与消费方的 **dict 键名要对齐**（`freq` 不是 `频率`）。
- 模型会漏掉它在说明里承诺的 helper 函数（`log()`、`file_mtime()`）——自己补。
- 中文星期转 int 用 `{'一':0,'二':1,'三':2,'四':3,'五':4,'六':5,'日':6}`，**绝不 `int('周一')`**。
- Windows 路径 join：`os.path.join('dir_', 'file.md')` 无尾分隔符时会把 `dir_` 当目录、file 变其子文件 → 用正规尾分隔符 + `os.makedirs(exist_ok=True)`。
