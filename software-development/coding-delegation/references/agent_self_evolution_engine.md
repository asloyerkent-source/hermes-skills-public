# Agent 自演化引擎（经验蒸馏成原则）— 可复用配方

> 场景：用户要赫米(3046)随时间"变智慧"而非堆记忆。本配方来自 2026-08-23 实做并通过多模型审(DeepSeek+GLM+硅基流动Qwen)。
> 核心认知：**记忆≠智慧**；变聪明靠"方法策略层(②)本地自演化"，不依赖官方模型升级。

## 范式（四层，共识自 Mem2Evolve/MindMemOS/SkillHub/CER）
事件驱动捕捉 → 语义蒸馏成原则 → 原则库检索应用 → 反馈闭环(强化/降级)

## 关键设计决策（经多模型审收敛，must-fix 已修）
1. **用户显式纠正("不对/不行/别")=燃料**。删除"沉默=弱正反馈"——沉默≠认可，否则无关垃圾原则缓慢升权污染库。
2. **蒸馏模型 ≠ 验证模型（必须不同架构）**：蒸馏用 Qwen2.5-7B-Instruct(硅基流动)，验证用 GLM-4-Flash。同源验证形同虚设。
3. **防反向污染三道闸**：
   - 黄金样本回归(硬编码5条只读: M30S查当日实价/删文件须拍板/数据不上网/3046主脑/记忆防污染)：新原则冲突即丢弃+[GOLDEN_CONFLICT]
   - 必填校验：缺 counter_example 或 source → 拒入库
   - 验证API失败 → 直接拒入库(confidence=0)，不保守放行(防垃圾)
4. **行为验证(L4)**：Agent 引用原则须展示具体执行动作，防"形式引用"假象。
5. **月度审计**：candidate区 activation_count=0 且超60天→修剪；污染行标polluted且retrieve跳过。

## 模型选型结论
- 蒸馏 Qwen2.5-7B（~¥0.0002/千token）非 Nex-N2-Pro：后者贵10-50倍且**实测两次空输出不稳定**，弃用。
- 成本 <¥0.05/月（蒸馏+判定+双模型验证）。3046 无GPU，全走 API。
- 写码走 external-model-coding 流水线：GLM 写码 + DS 审 + HY3 验收。

## 实现坑（实测）
- 蒸馏模型(Qwen)对极短指令式输入偶发返回非标准JSON → 解析失败须"失败即拒"(宁可漏抽不死库)。鲁棒提取：去```json包裹+re找首个{到末个}。
- 子模型后台写码时若自测联网失败会带崩整个任务不落盘 → 写码过程不联网(verify/retrieve/audit纯本地)，仅 distill 调API，落盘稳。
- write_file/patch 把含中文shebang的.py当binary → 改用 terminal 内 python heredoc 改写。

## 验收标准（跑通才算）
- `verify` → [VERIFY OK]（黄金冲突+缺反例逻辑有效）
- 真实 `distill` → 入库 → `retrieve --task` 命中（含"引用须展示具体执行动作"约束）
- 构造"把数据传到云端" → 被[GOLDEN_CONFLICT]拦，库不被污染

## 参考实现
$HOME/evolve.py（distill/retrieve/audit/verify 子命令，v0.3）。
设计草案：$HOME/evolve_arch_v03.py。调研笔记：/data/vault/备忘录/调研_Agent自演化方案借鉴.md。
