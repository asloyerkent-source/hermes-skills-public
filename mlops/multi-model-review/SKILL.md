---
name: multi-model-review
description: Use when 要多模型分析/交叉审/独立审稿人（并行视角，非对抗式挑战）。
color: "#4A90D9"
---


# 多模型审核（Multi-Model Review）

一句话定位：**用 ≥2 个真实不同的模型独立审同一份东西，再按加权共识收口** —— 主审 DeepSeek，输出落文件不刷屏，动手前先审。

> **本技能是 2026-09-26 并集合并产物**：原「多模型交叉审核」（实现侧：五模型全并行 v4 / curl 错误处理 / 加权共识）＋ 原 `mlops/multi-model-review`（流程侧：何时用 / 三档用法 / 纪律 / 踩坑）。两边是**互补并集不是取其一**：任何铁律 / 坑 / 命令 / 日期引用都不许丢。
> 归档在 `~/.hermes/skills/.archive/*-merged-into-multi-model-review/`，不删除可反悔（**含各源的 SKILL.md、references、scripts 及 `.bak-*` 历史备份**）。本次结构重整前的完整快照另存 `~/.hermes/skill-backups/cluster1-reskeleton-<ts>/`。
> **2026-09-26 结构重整**：SKILL.md 由 69KB 瘦身为「触发 + 铁律 + 选档 + 导航」，长文按主题下沉到 `references/`（v4 模板 / 档3 / 阵容 / 纪律 / 踩坑表）。**内容零删除，只换位置**；`触发` 一节做了 A/B 去重。

## 导航（先看这里）

| 你要做什么 | 去哪 |
|---|---|
| **选档：这次该用哪一档** | 下面「三档用法」 |
| 档3｜动手前的方案级双模型验证（**硬门**） | `references/stage3-plan-review.md` |
| 跑五模型全并行 / 完整 bash 模板 + 加权共识代码 | `references/v4-production-template.md` |
| 查有哪些 key、当前阵容、历史变更 | `references/roster-and-keys.md` |
| 静默交付 / 直连绕 Clash / 调用 cookbook / 实操坑 | `references/execution-discipline.md` |
| **找踩过的坑**（A 实现侧 + B 流程侧逐条原话） | `references/pitfalls.md` |
| 模型端点实测行为（超时 / 空响应 / 字段怪癖） | `references/model-endpoint-quirks.md` |
| LongCat / Qwen3-VL 专属怪癖 | `references/longcat_qwen_vision_quirks.md` |
| 直连 API 配方（GLM / DS / Kimi / LongCat） | `references/direct_api_cookbook.md` |
| 限流与配额实测 | `references/rate-limits.md` |
| **验判官偏差是真的**（受控实测：精简 vs 注水 + 位置互换） | `references/judge-bias-validation.md` |
| SiliconFlow 兜底策略与定价 | `references/siliconflow-strategy.md` |
| 3 阶段流水线（draft→GLM deepen→DS audit） | `references/multi-model-review-pipeline.md` |
| 诊断脚本与验证姿势 | `references/diagnose_verify.md` |
| 当前模型状态板 | `references/model-status-board.md` |
| 安全改 docker `daemon.json` | `references/docker-daemon-json-safe-edit.md` |
| 可跑脚本 | `scripts/pipeline_template.py`（3 阶段 draft→GLM deepen→DS audit，静默、cron 友好。⚠️ **仍 GLM-centric，用前按 2026-08-23 阵容改 GLM→LongCat/Kimi**）、`scripts/model_key_health.sh`（key 探活） |

## 触发

**何时用**：
- 用户要求「多模型分析 / 交叉审 / 审核验证 / 多模型分析论证下 / 多模型审核技能」，或任务结论依赖非平凡判断（数字引用、架构可行性、能力边界评估）需要可信度确认。
- 用户要第二个/第三个模型来 check、deepen 或 audit 作品。
- 用户建立「先写后审」流水线（例如「你用 HY3 写好之后，用 glm 再审查一下」）。
- 任何单模型容易做浅的交付物（HY3 在架构/深设计任务上偏浅）。
- **动手前的任何落地方案**（部署 / 架构 / 设备接管 / 安装「装什么、装哪里」）——必须多模型交叉，见 `references/stage3-plan-review.md`。
- 诊断/根因判断（网络 / 设备 / 性能类根因）也要多模型验证，GLM 优先（2026-08-16 强化）。
- **审一份多条目集合（规则库/纪律条目/风格指南）内部有没有自相矛盾** —— 关键词共现类机械检测必然产出垃圾，要走「机械统计客观量 + 多模型语义审（prompt 必须列伪冲突排除项）+ 逐条 grep 回源核验」，配方见 `references/pitfalls.md`。

**何时不用 / 别误用**：
- **禁止把单模型（含 hy3 多实例）自查标成「多模型审核」** —— 用户明确点名此误导（原话「你自己审核的视角不够全面」）。必须 GLM主审+DS复核 或 DS+GLM 交叉，或走五路并行。
- **不要为了「交叉验证」再调第二个模型**：爬虫/情报类交付物要求「只基于抓取内容不编造」，靠 prompt 硬约束 + 低温即可，双调用违反不烧额度铁律（2026-08-20 DS 审计抓出）。
- **多轮审核必须换模型，否则第四轮起是无效功。** 连续 3 轮同一模型后，它开始命中前几轮**自己已经建立的框**（如把前轮结论当成既有事实继续推），而真正的真缺陷迟迟不出现。实测：三轮同模型共报 63 条、全部低价值；第四轮换模型立刻挖出前三轮都漏的真 bug（frontmatter 闭合符缩进）。
  - **判据：审稿模型报出的新缺陷若都能被前几轮报告「解释」，说明它在自己给自己圆场，不是独立审查。** 见到这种收敛趋势就换模型，别加轮次。
  - ⚠️ **`delegate_task` 不接受 per-task 模型参数** —— 子代理固定走 `config.yaml` 的 `delegation.model/provider`，在任务描述里写「换个模型审」是无效的，派出去的仍是同一个模型（实测连派两个「不同模型」的审稿人，返回的都是同一模型）。**真要换模型走 CLI**：`hermes chat -q <prompt> -Q --provider <p> -m <model>`，输出 `> file.txt` 落盘。
  - 换之前**先探活**：`hermes chat -q "只回复两个字：可用" -Q --provider X -m Y`，逐个候选跑一遍再挑活的。记忆里「某模型欠费/不可用」是快照，每次换阵容都要重测——实测一条欠费旧账早已作废。
- 不要用 Nous Portal 调 GLM/DeepSeek（既 404 又扣 Nous 额度）；走官方直连。

### ⚠️ 「同一厂商」要看**调用渠道**，不是看模型名后缀

用户拥有某厂商的官方 key 时，**必须用它，不要用第三方门户转发的同名模型**——
门户后面挂的可能是完全不同的权重，也可能是同一家的蒸馏版，两种情况下这一票的交叉价值都归零。

实测：凑第三票时选了第三方门户的 `qwen/qwen3-8-flash`当「阿里 Qwen 的交叉票」，
用户直接纠正「我们 qwen 的 key，不是 nous 平台的 qwen 模型」——
换成自有 key 直连厂商旗舰模型后，它提出的判断（**循环验证：gold 由关键词规则标注，
于是规则基线就是天花板**）是另两家都没提的，且经实测证实。

**规则**：
- **交叉票的独立性由「厂商 + 权重」决定，模型名里的厂商名不算证据。**
  门户名下的 `vendor/model` 只能证明「这个门户提供它」，不能证明「这家厂商的模型」。
- **用户自有 key 直连官方端点 > 门户转发**，即使门户那条更便宜或更快。
  计数「≥N 个不同模型」时，**门户转发与它标称的厂商不能算两票**。
- **付费/自有 key 的旗舰模型可以顶主审或交叉位**，「免费模型不顶主审」这条限制的是
  *额度不可靠*的渠道，不是*模型质量*——用自有 key 时按模型实际能力定位。
- 派审稿前先 `grep` 一遍 `config.yaml` 的 providers 列表，**用户可能已经配了他自己的 key**
  而你没看见（本场就有 `dashscope`）。不要在门户上凑第三票。
- **免费/自有 key 的审稿输出可能长时间是 0 字节而进程还活着** —— 门户转发的模型
  在长 prompt 上可能跑到超时（实测跑 6 分钟无输出、杀掉后文件里只有中断信号）。
  **判据：字节数 0 且进程在 ⇒ 不等于「快好了」，也不要立刻换模型并排；先设超时，
  超时后再换。** 同理，付费/自有 key 的模型通常更稳（本场换成自有 key 直连后一次跑通）。
- 选渠道时顺手报成本：自有 key 的旗舰模型一次审稿的 token 量级，让用户知道这不是免费池。
- 指定 Claude Code/Pi/Codex 出方案时，不要用其他工具替代后还声称是对方产出（见铁律「指定 agent 必须真调」）。

## 用户铁律（绝不可违反）

### A ｜用户铁律（2026-08-31 定，绝不可违反）
1. **主审必须是 DeepSeek**：DeepSeek 主审 + GLM-5.2/Qwen3.7+ 二审 + Kimi 三审 + LongCat 兜底。LongCat 免费但不顶主审。
2. **模型名精确（2026-09-27 实测更正）**：DeepSeek 官方 `/v1/models` 现只返回两个 ID —— **`deepseek-flash`**（= DeepSeek-V4.1-Flash，1M 上下文，effort low/high/max，支持图片输入）与 **`deepseek-v4-pro`**（= DeepSeek-V4-Pro）。**`deepseek-chat` 已不在模型列表中**，但作为旧别名仍可调用，响应体 `model` 字段回 `deepseek-flash`；`deepseek-v4-flash` 这个名字**不存在**，别用。Kimi → `kimi-k2.7-code`（直连 api.moonshot.cn，限 3RPM，temperature 必须=1）；GLM → `glm-5.2`（2026-09-27 实测欠费 429，不可用）。⚠️ P0-5 修复：不同模型名可能映射到同一底层模型，**去重必须按响应体 `model` 字段**，不能按请求模型名。
3. **Kimi 必须 temperature=1**：传 0.3 等报 400。LongCat/DeepSeek 可 0.3。
4. **"多模型分析论证下"是动手前的硬门**：论证阶段只读诊断 + 写方案到文件，不碰目标机。
5. **空响应 = 不可用**：某模型返回空/429 → 标记失败，不伪造意见，不重复烧额度。
6. **DS 审计读 reasoning_content，但必须验完成度**：DeepSeek 有时把结论放 reasoning_content 而非 content，必须读 `content or reasoning_content`。⚠️ 这个兜底会把**被截断的思考稿**当成成品递回来——思考稿有标题有表格、读起来像完整报告，只是结尾半句断掉，肉眼极易误收。**收下任何模型输出前先看 `finish_reason`**：不等于 `stop`、或 `completion_tokens` 顶满 `max_tokens` → 一律判「截断」，按任务规模加大 `max_tokens` 重跑，绝不把草稿当交付（细节见 `references/pitfalls.md`）。
7. **并发验证独立进程**：同进程 threading 边写边读会假阳性，必须独立进程读写分离。
8. **完整上下文包**：派任务给模型 B 时，必须传完整背景包（全局约束 + 已决策 + 已知坑 + 草稿），不要截断。
9. **审计 prompt 逼出红线**：要"动手会不会崩/丢数据"，不要"写得不错"。明确要最高危 N 条 + 具体命令/路径 + 能否一次性搞定。
10. **安装/部署方案也必须先多模型审**：即使是"装什么、装哪里"也要交叉验证再动手。
### A ｜三条执行铁律（2026-08-30 定）
1. **无回复立即换模型**: 超时/空响应/格式异常 → 不重试烧额度, 立刻标记失败并换下一个。
2. **结论有效性门槛**: 有效结论须 **≥3 个不同模型**给出结果。不足 3 个 → 标"样本不足, 不采纳为定论"。Hermes 主审算 1 个。
5. **定期联通测试 key**: 每周 cron 跑 `model_key_health.sh`, 失败 key 立刻 Telegram 告警。
> 注：原文件编号就是 1 / 2 / 5（无 3、4），照实保留，未改号。
### A ｜推荐调用顺序（铁律）
默认: **DeepSeek(主审)** → **GLM-5.2(二审)** → **Qwen3.7+(三审)** → **Kimi(四审)** → **LongCat(兜底)**

某模型挂了跳过，继续下一个，直到凑满 ≥3 个有效响应。
### B ｜2026-08-31 用户铁律纠正（阵容 + 流程）

> **主审必须是 DeepSeek 或 Kimi，免费模型不顶主审。** 用户原话："应 deepseek 或者 kimi 主审，其他二审三审随意"。误用 LongCat/Step/Laguna 免费三模型当主审 = 错。正确：DeepSeek主审 + Kimi二审 + LongCat/Qwen3三审。
> - **Kimi 模型名已变**：`moonshot-v1-8k` 已 404 下线 → 必须用 `kimi-k2.6`（或 `kimi-k3`）。hermes 里 Kimi provider 默认模型名若仍是 `moonshot-v1-8k` 会 404，调用前查 `/v1/models` 或写死 `kimi-k2.6`。
> - **key 在 ≠ 通道通**：`devops/credential-inventory-audit/scripts/key_inventory.py` 验 key 存在 ≠ 模型名有效。审前两步都要验：① key 在 .env（python 正则读文件，勿用裸 `os.getenv` 误判空）② 模型名在目标端点有效。
> - **免费三模型（LongCat/Step-3.7-Flash/Laguna-S-2.1）只作交叉/兜底，不顶主审。**

> **流程纠正（本场踩坑）**：
> - **"多模型分析论证下" 是动手前的硬门**：论证阶段**只读诊断 + 写方案到 .md**，不碰目标机。本场 agent 没论证完就反复 ssh 试探 Vulkan、设环境变量、装软件 = 跑偏被叫停。
> - **`hermes chat` 跑论证会造垃圾会话**：每个 `hermes chat` 默认建 session，本场因此多出一票空标题会话要清。论证输出用 `> file.txt` 落盘（或 cron no_agent），**绝不 `hermes chat` 建会话**。清垃圾用 `hermes sessions delete <id> --yes`。
> - **key 误判"丢失"是 agent 的错，不是用户的**：裸 `os.getenv` 不加载 .env → 读到空 → 反回头问用户发 key = 制造泄露风险 + 惹用户。查 key 只跑 `devops/credential-inventory-audit/scripts/key_inventory.py`（仅显前缀+长度），**绝不在对话里向用户索要 key**。密码册在 `~/HermesShare/*.md`。
### B ｜方案级双模型验证（user 2026-08-14 硬纪律, 超出审案）
- 任何全面落地方案(部署/架构/设备接管)须≥2模型交叉验证(HY3+DeepSeek 或 DS+GLM)再定稿, 禁单模型拍板。不止交付物审查, 动手前的方案本身必须双模型交叉。
- **安装/部署方案也必须先多模型审**：用户明确要求"多模型分析论证安装流程方案，做好准备工作再开始下载安装"。即使是"装什么、装哪里、怎么装"这类看似简单的决策，也要把方案草稿（含模型列表、显存需求、下载大小、框架选择）喂给 DeepSeek+LongCat 交叉验证，避免装到一半发现硬件不兼容（如 P620 CC 6.1 装不了 PyTorch 2.1）。
- OpenClaw(小龙虾)类项目 user 定 A: 继续用赫米不另装, 但动手前须参考其架构(HEARTBEAT.md心跳契约/ClawHub技能市场/文件即配置/mission control)改进赫米, 不凭空造轮子。
### 跨技能铁律（A/B 两侧共同沉淀）
- **一致 ≠ 正确：多模型会「同向过度泛化」，必须实测核验（2026-09-27 血案）**: 四个模型（DeepSeek/Qwen3.7+/Kimi/LongCat）对同一份材料**全部**判出同一条「致命」结论——「免费档模型忽略 system role，所以改 SOUL.md 无用」。实测直接推翻：免费档 `stealth/space-bunny-alpha` 在 system role 下 100% 遵循硬规则（回 `PINEAPPLE42`）、风格规则（回 `[ZQ7] Hello!`）、禁套话规则（直接答、无开场无复述）。根因是它们把源码里一条**只针对分类任务**的窄观察（tier-router 注释：分类调用时模型去答用户请求而不是分类）泛化成了普适定律。**铁律：多模型共识只是「值得信的假设」，凡结论可实测（发一次 API / 读一行源码 / 跑一条命令）就必须实测再采纳，禁止把 4/4 一致当结论直接汇报。** 用户问「这样做有用么」时，实测证据 > 模型票数。
- **模型不认路：方案里出现的文件路径一律先验证再执行**: 让模型出「落地方案」时，它们会写出**看起来专业但根本不存在**的路径——典型是把早已合并归档的旧技能名当现役文件名用（`pi-delegation/SKILL.md`、`codex-delegation/SKILL.md` 全部不存在，真实文件是合并后的 `coding-delegation`）。四个模型独立给出的方案可以**全部**指向同一个不存在的文件：共识在这里零保护作用，因为它们谁也不查你的磁盘。**动手前逐条确认目标文件真实存在**（用 `search_files` 按名字去找，不要信模型给的文件名），把模型给的文件名当线索而非事实，回给用户的方案一律写实测到的真实路径。同场第三个例子：模型写的 `prompt_optimizer.py` 不存在，实际是 `flows/prompt-optimizer` 技能下的 CLI。
- **模型提的改法要先跟本地已有纪律对撞一次**: 模型不知道你技能库里已写死的约束，会提出与现有规则**直接矛盾**的方案（例：某技能明令「发给下游 coding agent 的 prompt 必须是纯 ASCII 英文，中文会被 homoglyph 扫描拦截」，而某优化器被设计成「输出语言与原文一致」即输出中文——两者不能同时生效）。审方案时逐条问「这条改动撞不撞已有铁律」，冲突要在方案里当场判掉，不要让两套互斥规则一起落地。 **根因**：模型没读过那个文件，方案必然锚在想象上——审一份要改的文件前，必须把该文件的**真实内容**（或至少真实路径清单）放进上下文包。
- **指定 agent 必须真调（2026-09-15 铁律）**: 用户指定 Claude Code/Pi/Codex 出方案或执行时，**必须真的调用那个 agent**。没跑通就直接说"没跑通"+报错信息，**绝不擅自用其他工具替代后还声称是对方产出**。反例：用户要 Claude Code 出方案 → 实际 curl DeepSeek API → 汇报时声称"Claude Code 方案"。这是欺骗。
- **用户说停/晚安 → 立刻停（2026-09-15 铁律）**: 用户说"晚安""停""不需要了" → **立刻停止所有操作**，不跑后台任务，不拖泥带水。反例：用户说晚安 → 我继续跑 git push / 后台任务 → 用户早上发现还在跑。
- **多模型审核须真多模型**: 禁止把单模型(含 hy3 多实例)自查标成"多模型审核"(用户点名误导)。必须 GLM主审+DS复核 或 DS+GLM 交叉，或走五路并行。
- **推理/视觉模型输出绝不轻信（用户"核查铁律"的延伸）**: 模型说"X偏离/异常"先写代码核验（本次 LongCat 编造被代码推翻）。
- **memory 只记实际发生的事（2026-09-15 教训）**: 计划中的事、伪装成"Claude Code 方案"实际是 DeepSeek API 的结果——这些**不能写入 memory**。memory 只记录：实际执行了什么、实际产出了什么、用户确认了什么。
  （「评审者只批评、不给修法」已作为硬铁律写在 memory 的[硬·派活时]条，此处不重复。）
- **判官有系统性偏差：多模型评审本身会被四种偏差污染**（2026-09-28 提取自 agent-evaluation）: 模型当评审时不是中立裁判，偏向是可预测的：

  | 偏差 | 表现 | 缓解 |
  |---|---|---|
  | **位置偏差** | 成对比较时排在前面的被偏爱 | 交换位置各评一次，取一致结果 |
  | **篇幅偏差** | 越长分越高，与质量无关 | 提示词显式声明忽略长度 |
  | **自我增强偏差** | 模型给自己或同族输出打高分 | 生成方与评审方用不同模型 |
  | **权威偏差** | 语气笃定、置信度高的被高估 | 要求给证据/出处，加核查层 |

  另：**偏好类判断用「成对比较」比「单独打分」更接近人类**（MT-Bench 结论）；客观类（事实准确、指令遵循）才用单独打分。
  **关键推论**：**判官与人类高度一致不如「系统性分歧模式」重要** —— 一个稳定在某个维度上判错的评审，比随机噪声更值得排查。这解释了上一条「4/4 一致 ≠ 正确」：四家若同族或同源，自我增强偏差会让它们**同向偏移**，一致反而可能是偏差叠加的信号。

  > ⚠️ **实测状态（2026-09-28）：长度偏差未复现 —— 别把上表当已验证的定律，它是待检验的假设清单。**
  > 15 轮受控实测（4 模型 × 明暗两种注水 × 顺序互换；同一材料的精简版 vs 注水版，**事实相同、只差铺陈**）：
  > - 注水版仅被选 **1/15（7%）**。「明显废话」组 **0/8**（精确二项 p=0.0039，**可拒绝「无长度偏好」**）；「专业但啰嗦」组 1/7（p=0.063，同向但样本不足）。
  > - 位置偏差未达显著（选位置A 9/15 = 60%，p=0.30），但 **qwen3.7-plus 单模型 4 轮里 3 次选 A**，有个体迹象。
  > - **结论：本设计下这批判官主动偏好精简，长度偏差不成立。**
  > - 局限（不能忽略）：每格 n=1 功效低、材料单一、隐蔽注水版仍带独立「背景/总结」段可能仍易识别。
  > - **复现**：`scripts/judge_bias_test.py`（改材料即可重跑）+ `scripts/analyze_bias.py`（含精确二项检验）。
  > - 实测坑：kimi 账号 **RPM 上限只有 3**，连调会被限流误报 400/429——排查模型行为前先确认不是自己的调用频率问题。

## 三档用法（先选档）
### 档1 ｜分阶段审核（重交付物）
Run a deliverable through 2–3 models in stages: a draft model → a deepen model → an audit model.

**Workflow (3 stages)**：
1. **Draft** (HY3 or default): produce the base deliverable as a local `.md` file. Do NOT print it to chat.
2. **Deepen** (GLM / strong-reasoning model): take the draft + full context, produce a deeper/executable version.
3. **Audit** (DeepSeek / critical model): review the deepened version for feasibility, omissions, command correctness.

**配套：6 步工作流（A 侧）**：
1. **准备**: 加载 .env key, 确认 ≥3 模型可调用。
2. **分发**: 将审核目标 + 原始材料发给各模型, 各模型独立给出结构化发现（问题/位置/严重度/建议）。
3. **并行审**: 各模型同时跑, 超时/空响应 → 立刻切池内下一模型（铁律 1）。
4. **综合**: 合并发现, 标"共识"(≥2 模型同指) vs "单模型主张"(仅 1 模型说)。
5. **引证核验**: 对关键声明做源码/web/实测验证（见下）。
6. **落盘 + 回写**: 结论写入知识库；审出的缺陷/坑回写 `references/pitfalls.md`（原 SKILL.md「陷阱」节已下沉到该文件）。

**引证核验规则（borrowed from PolyBrain）**：对每个事实性声明, 必须标注验证状态:
- **[verified]** — 通过源码行 / web_extract / 实测 三选一验证通过
- **[INVALID]** — 验证失败（源码或实测反驳声明）
- **[unverified]** — 无法溯源, 不纳入最终结论

**全上下文包（CRITICAL: full context package, user correction）**：
> "对3个项目，应该做个详细的资料作为其他2个模型整理的信息，不然很容易遗漏"

When handing a task to model B, **do NOT pass only the truncated draft**. Assemble a **complete background package** document containing:
- Global constraints/disciplinary rules the user has set (e.g. silent-output rule, model-routing policy, privacy boundaries).
- All already-decided decisions and known pitfalls (e.g. from a prior dual-model review).
- The HY3 draft itself.

Pass this whole package (not `draft[:3500]`) into the deepen/audit prompt. Truncating causes the second model to miss decisions and produce shallow or contradictory output — observed: GLM output jumped from ~150 chars (truncated input) to ~1400 chars (full package).
### 档2 ｜五模型全并行交叉审核（要共识结论）
**A 的 v4 策略**：不要串行、不要两阶段。**五个模型一次性全部并行发出**，谁先回谁先落盘，最后统一收口算加权票（绝对票数制，≥6/10 采纳）。完整实现见 `references/v4-production-template.md`（原「生产模板：五模型全并行 v4」与「加权共识算法（绝对票数制）」两节已整体下沉到该文件）。

何时选这档：需要**一个可量化的共识结论**（APPROVE/REJECT/MODIFY + 10 分标尺），而不是"多听几个意见"。

> **档3｜方案级双模型验证（拍板前）** 是动手前的硬门，正文较长 → 见 `references/stage3-plan-review.md`。
