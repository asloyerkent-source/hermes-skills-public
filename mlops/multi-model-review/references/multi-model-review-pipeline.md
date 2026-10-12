# 多模型深加工流水线（HY3→GLM-5.2→DeepSeek）实战模板

> 来源：2026-08-14 三任务（阶段1手册/代理抖/数字管家）深加工。复用模式，非一次性的。
>
> ⚠️ **2026-09-26 状态更新（原流程里的模型已变）**：
> - **HY3 免费结束**（2026-09-01 起转付费 $0.11/1M in + $0.42/1M out），不再作免费起草层；免费起草可用 `stealth/space-bunny-alpha` 或 `nousfree` 免费档。
> - **GLM-5.2 欠费**（HTTP 429 余额不足或无可用资源包），深加工层需先充值或改用 DeepSeek / `glm-4-flash`。
> - **LongCat 下架**：`meituan/longcat-2.0:free` 调用 404（已永久下架）；官方直连 `LongCat-2.0` 仍在，但免费资源包 2026-09-22 到期作废。
> - 当前免费档名单与轮换见 `mlops/hermes-model-routing/references/free-tier-archive.md`；路由现状先跑该技能的 `mlops/hermes-model-routing/scripts/probe_providers.sh` 实测。

## 何时用
用户对一份方案要"深度加工 + 独立审核"，且想用 GLM-5.2 + DeepSeek 充值 key 分担 HY3 的浅（HY3 规划/记录够，但深加工/审案易浅）。

## 黄金流程（实测有效）
1. **HY3 起草**：先出草稿（不依赖任何外部模型，最快）。
2. **写「完整资料包」**：汇总全局纪律 + 已定决策 + 坑 + 给模型的指令，单独成文件（如 `三项目资料包.md`）。
   - 关键教训：早期直接把草稿 base[:3500] 截断喂 GLM，它拿不到已定约束 → 漏决策、出浅。改成喂完整资料包全文（不截断），GLM 产出从 151 字涨到 1445+ 字。
3. **GLM-5.2 深加工**：裸 requests 直连 open.bigmodel.cn/api/paas/v4（model glm-5.2，见 SKILL.md 直连段），prompt = 资料包全文 + HY3草稿 + "针对本任务深加工：命令级步骤+验证+坑+回滚"。max_tokens<=1000。
4. **DeepSeek 审核**：直连 api.deepseek.com/v1（proxies={} 绕 Clash），prompt = 资料包关键约束 + GLM 产出。max_tokens<=500。
5. **最终综合报告**：DS 融 HY3草稿+GLM深加工+双模型审案修订+资料包，出命令级终稿+风险表+返工预防清单。

## 限流应对（实测）
- GLM-5.2 免费额度：时好时坏，长输出必截空。短输出 + 错峰（cron 03:00）+ 退避重试（10s*n，最多4次）+ 真失败即退不硬耗。
- DeepSeek 直连（充值 key）：偶发空回，多因 Clash 代理抖 → 必须 proxies={"http":None,"https":None}。
- 流水线落 cron（静默、写文件不 print），低峰自动补失败的环节。

## 脚本骨架
- glm_ds_pipeline.py：JOBS 列表（HY3文件, GLM-5.2输出, DS审输出, 任务名）；循环调 GLM-5.2 再调 DS；全程 log() 写本地日志不 print（静默纪律）。
- 读 key 从 .env 文件（不假设 os.environ 有）；GLM-5.2 base https://open.bigmodel.cn/api/paas/v4，DS base https://api.deepseek.com/v1。

## 用户纠偏（重要）
- 用户："用 GLM 再审查…做详细资料包防遗漏" → 必须给模型完整背景包，不能甩缩略草稿，否则模型漏掉已定约束。
- 用户："DeepSeek 是你充值的 key 不是免费" → DS 直连扣余额，非 Nous 免费档；之前误报"免费档限流"是口误，真因是代理抖/偶发截断。
