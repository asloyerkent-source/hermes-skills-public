# LongCat-2.0 / Kimi / Qwen3-VL 实测特性 (2026-08-23, 3046 直连验证)

> 配套 `SKILL.md` 的 2026-08-23 新增段。本文件是知识库, 非镜像官方文档。

## 调用速查
| 模型 | endpoint | model 串 | key (.env) | 取响应字段 |
|---|---|---|---|---|
| DeepSeek V3 | https://api.deepseek.com/v1/chat/completions | deepseek-chat | DEEPSEEK_API_KEY | content or reasoning_content |
| LongCat-2.0 | https://api.longcat.chat/openai/v1/chat/completions | LongCat-2.0 | LONGCAT_API_KEY | **reasoning_content** (content 常空) |
| Kimi K2.6 | https://api.moonshot.cn/v1/chat/completions | kimi-k2.6 | KIMI_API_KEY | content or reasoning_content |
| Qwen3-VL-8B | https://api.siliconflow.cn/v1/chat/completions | Qwen/Qwen3-VL-8B-Instruct | SILICONFLOW_API_KEY | content or reasoning_content |
| Qwen2.5-7B | https://api.siliconflow.cn/v1/chat/completions | Qwen/Qwen2.5-7B | SILICONFLOW_API_KEY | content or reasoning_content |

取响应统一: `msg.get("content") or msg.get("reasoning_content")`。
读取 key: `re.search(r'NAME=\s*(\S+)', env).group(1)` 再去 `.strip("'").strip('"')`。
国内 API 直连, requests 用 `trust_env=False` 或 `proxies={}` 防继承 Clash 代理 SSL 失败。

## LongCat-2.0 深度特性
- **纯文本, 不能看图** (vision 交 Qwen3-VL)。误用于看图会返回"看不到图片"。
- 输出在 `reasoning_content`: 它会先复述任务+分析过程, 结论在尾部。max_tokens 给足(400-900)否则结论被截断。
- **会编造 (推理模型通病)**: 曾说"单价1.52/1.65偏离", 但源卡里根本没有逐行单价 —— 凭语境补全的幻影。
  → **任何 LongCat 输出必须用代码/实测核验**, 这是用户"核查铁律"的延伸。本次 longcat 编造被一行代码推翻。
- 1M 上下文真强项: 整批吞 26 张物料卡做跨卡交叉, 揪出逐卡看不出的错乱 (合同号≠产品字段、数量残缺)。DeepSeek/Kimi 单批吃不下这么全。
- 能发标准 tool_calls (agent 编排可用)。

## Qwen3-VL 深度特性
- ✅ 能看图, 中文描述准确自然 (实测 5 张 camera 照质量好)。
- 单张图 ~15500 prompt token (图本身占大头, 输出才 20-30)。全量 6481 张 ≈ 1 亿 token, 不现实 → **必须抽样** (每年 N 张)。
- 硅基视觉模型名必须 `Qwen/` 前缀 + Qwen3-VL 系列; `Qwen/Qwen2-VL-7B-Instruct` 已不存在 (报 "Model does not exist")。
- 硅基视觉列表实测有: Qwen3-VL-8B/32B-Instruct, Qwen3-VL-30B-A3B-Instruct, Qwen3-Omni-30B-A3B-Instruct。

## Kimi K2.6
- 返回结构也可能用 reasoning_content, 取字段双字段兜底。
- 本场定位代码二审。
- ⚠ **temperature 硬限制**: Kimi K2.6 **只允许 temperature=1** (reasoning 模型)。传 0.3 会直接 400 `invalid temperature: only 1 is allowed for this model`。调用务必 `temperature=1` (本会话实测踩坑: 传 0.3 首轮失败, 改 1 才通)。

## LongCat 截断重试模式 (本场实测)
- LongCat 先复述任务再分析, 结论在尾部。给 max_tokens 仍可能卡在 reasoning 中段被截断 (本场多次: 输出断在"B部分中段"/"起草-逐节进行")。
- **对策**: 若首轮结论被截断, **重跑时改 prompt 只要求输出缺失段** (如"只给B和C部分"), 并适当降 max_tokens 聚焦。不要盲目加 max_tokens (会让 reasoning 吃满又截断)。
- 取响应后若 content 空但 reasoning_content 有实质, 直接把它当结论用 (同 DS 审计套路)。

## 端到端多模型交叉审实测 (本场 evo v0.4 立项的真流程)
实际跑通链路: 搜集(web_search 多轮) → LongCat执行三审(全景/跨文档) → DeepSeek主审(架构可行性) → 写方案v1 → Kimi代码二审 + LongCat复审 → 修订v2。
- **两模型独立抓出方案真缺陷** (非走过场): Kimi 抓伪技能/锁JSON损坏/命中注水/向量库增复杂度; LongCat 抓阶段C-SMB破本地主权 + 阶段E收外部数据违不联网底线。二者交叉印证"单模型审会漏"。
- 印证技能铁律: 多模型交叉审必须显式把"找逻辑漏洞/底线冲突"写进 prompt, 不只问"有没有bug"。

## 用户 2026-08-23 阵容定稿 (覆盖旧 GLM 主力)
DeepSeek主审 + LongCat-2.0执行三审 + Kimi K2.6代码二审 + Qwen3-VL视觉 + Qwen2.5蒸馏。
**GLM 已弃用**, 旧 "HY3→GLM→DeepSeek" / "GLM当验证器" 分工作废。若复用旧 evolve.py, 验证器改 DeepSeek 或 LongCat。

## 踩坑备忘 (本场, 已代码核验纠正)
- longcat 误用于看图 → 纯文本, vision 归 Qwen-VL。
- 目录匹配 bug: `cno in r` 误匹配子目录 → `os.path.basename(r)==cno`。
- 模型输出不核验就信 → longcat 编"单价偏离"被代码推翻。
- f-string 嵌套中文括号/括号语法错 → 改字符串拼接。
