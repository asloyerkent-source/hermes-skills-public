# 踩坑总表（A 实现侧 + B 流程侧，逐条原话）

> **本文件是 `multi-model-review` 技能的支持文档。**
> 来源：2026-09-26 从 SKILL.md「踩坑总表」整节下沉。A/B 两侧是并集，**宁可重复不可遗漏**。

---

## 踩坑总表

> 合并 A 与 B 的全部坑。**每条保留原始日期与原话引用**；宁可重复，不可遗漏。
### A ｜ 陷阱（Pitfalls，实现侧技能原文）
- **GLM-5.2 已接入**: provider `glm`，`open.bigmodel.cn/api/paas/v4`，`glm-5.2`，keyenv `GLM_API_KEY`。旧版 GLM 4.x 系列 key 已删除，勿再引用。⚠️ max_tokens >150 时响应 >12s 易超时，轻任务设 150 以内。
- **DeepSeek 直连恢复**: 模型 `deepseek-chat`。
- **Kimi temperature 硬限=1**: 只传 1，不传 0.3。
- **LongCat 兜底**: 取内容用 `msg.get('content') or msg.get('reasoning_content')`。
- **并发写测试假阳性**: 验证追加写安全性须用**独立进程**, 同进程 threading 边写边读会读到半行报"全损坏"。
- **key 在 .env 不在 shell env**: 多模型脚本必须 `set -a; source $HOME/.hermes/.env; set +a`。
- **PII/私有数据出网审查**: 含私有数据 → 必须先给用户确认, 不得无人值守批量喂云端模型。
- **DS 审计读 reasoning_content**: DeepSeek 有时把结论放 reasoning_content, 必须读 content or reasoning_content。
- **审计 prompt 逼出红线**: 要"动手会不会崩/丢数据", 不要"写得不错"。
- **安装/部署方案也必须先多模型审**: 即使是"装什么、装哪里"也要交叉验证再动手。
- **⚠️ Pi 子进程不继承 .env（2026-09-18 实战）: Pi 子进程是独立 session，不继承 ~/.hermes/.env 中的 key。多模型脚本必须 `set -a; source $HOME/.hermes/.env; set +a` 显式加载，否则返回 "No API key found"。
- **⚠️ 指定 agent 必须真调（2026-09-15 铁律）**: 用户指定 Claude Code/Pi/Codex 出方案或执行时，**必须真的调用那个 agent**。没跑通就直接说"没跑通"+报错信息，**绝不擅自用其他工具替代后还声称是对方产出**。反例：用户要 Claude Code 出方案 → 实际 curl DeepSeek API → 汇报时声称"Claude Code 方案"。这是欺骗。
- **⚠️ Pi 自报不可信（2026-09-15 实战）**: Pi 自报"修了"但实际未生效。Hermes 必须独立验证：Pi 说修了 → 读真文件 / 真跑命令确认。Pi 说"6/6 全修完" → 逐条验证，发现 2 条未落地。
- **⚠️ 用户说停/晚安 → 立刻停（2026-09-15 铁律）**: 用户说"晚安""停""不需要了" → **立刻停止所有操作**，不跑后台任务，不拖泥带水。反例：用户说晚安 → 我继续跑 git push / 后台任务 → 用户早上发现还在跑。
- **⚠️ memory 只记实际发生的事（2026-09-15 教训）**: 计划中的事、伪装成"Claude Code 方案"实际是 DeepSeek API 的结果——这些**不能写入 memory**。memory 只记录：实际执行了什么、实际产出了什么、用户确认了什么。
- **⚠️ 3046 网络先 curl 验证再决定走代理（2026-09-15 修正）**: 3046 有直连和代理两种出网方式。不要假设"所有外部网络必须走代理"——先 curl 测试直连，通就不用代理。之前误判 GitHub 必须走代理，实际是 curl 参数问题。
### A ｜ 五模型全并行 v4 修复记录（F1–F7，2026-09-16）
- **F1 阈值自相矛盾** —— 现象：Phase 1 串行跑完 3 个模型后就短路宣布"达成共识"，4/9 或 5/9 也被当成一致结论输出；根因：短路的判据（"过半数/够 3 个就行"）和加权阈值（≥6/9）是两套互斥规则，短路绕过了加权规则；修法：**删掉 Phase 1/Phase 2 与一切短路**，五模型全并行跑完，一律由 `consensus()` 按绝对加权票判决（≥6 采纳 / 4–5 部分一致 / <4 无共识）。
- **F2 "两阶段省钱"是假的** —— 现象：设计假定 Phase 1 常能出共识、于是省掉 Phase 2 的开销；根因：对开放式审核任务，三个模型对 verdict 的一致率实测只有 **30–50%**，也就是说 Phase 2 基本每次都要跑；串行总耗时 = 90s + 45s = **135s**，比一次性全并行的 **90s** 还**多花 45s**；修法：**放弃两阶段，直接五路并行**，耗时天然等于最慢模型。
- **F3 curl 错误处理把失败伪装成空串** —— 现象：模型挂了却报告"无意见"，HTTP 错误码和超时全被吞掉；根因：`curl` 把 **stderr 混进 body 文件**、又用 `-w` 把 HTTP 码**追加在 body 末尾**，取码用 `tail -1`（body 一有换行就取错行），随后 `json.load()` 抛异常、`extract_text()` 静默 `return ""`；修法：`-o "$body" -w '%{http_code}' > "$code" 2> "$err"` 三路分离，`code=$(cat "$code")` **绝不用 tail -1**，显式区分 **EMPTY / HTTP xxx / TIMEOUT(28) / PARSE_FAIL**，**JSON 解析失败绝不退化成空字符串**。
- **F4 等待没有挂钟上限** —— 现象：担心 `wait` 会无限挂起；根因：对 bash 后台任务缺少全局超时兜底的概念；修法：**已解决，且无需额外超时包装** —— 每个 curl 各自带 `--max-time`，**五路并行天然以最慢模型（90s）封顶**，所以 `wait` 必然在 90s 量级返回，不需要再加外层 timeout。
- **F5 get_verdict 正则误抓 + 永远退出 0** —— 现象：正则可能从 `findings` 的**散文描述**里捞到一个关键词（比如 reviewers 说"不要 APPROVE"却被读成 APPROVE），而且脚本无论结果如何都 `exit 0`；根因：没有"先结构化解析、后兜底"的分层，且退出码没跟共识结果挂钩；修法：**先 JSON 解析且只读顶层 `verdict`**，正则**只作为 JSON 失败后的兜底**；同时定义退出码：**达成共识=0，其余=1**。
- **F6 模型参数硬编码到处散落** —— 现象：endpoint/model/keyenv/temperature/max_tokens/timeout/weight 散在流程各处，改一个模型要翻半个脚本，极易漏改（Kimi temperature=1 这种必填项最容易漏）；根因：没有中心配置；修法：引入 **bash 关联数组配置表** —— `EP / MODEL / KEYENV / TEMP / MAXTOK / TIMEOUT / WEIGHT` 七个字段 + `MODELS` 数组，**加一个模型 = 每张表加一行**，其余代码零改动。
- **F7 UNKNOWN 被当成"大家都一样"** —— 现象：两个模型都解析失败、都得到 `UNKNOWN`，被 `[ "$a" = "$b" ]` 判为相等，从而**误报为达成共识**；根因：`UNKNOWN` 被当成一个正常 verdict 参与比较和计票；修法：`UNKNOWN` **永不进票桶、永不进权重分母**，`get_verdict` 里任何不在 `{APPROVE,REJECT,MODIFY}` 的返回值一律归为 `UNKNOWN` 并跳过。
### A ｜ ⚠ curl 后台进程陷阱（2026-09-16 实战，F3 相关但独立）
`curl ... &` 后台进程的 stdin = /dev/null，**`-d @-` 会立即读到 EOF，发送空 body**。模型收不到 prompt，返回空或报错。
- **修法**：把请求体先写入临时文件（`$WORK/$k.req`），用 `curl -d @"$WORK/$k.req"` 从文件读。
- **说明**：这不是 F3 三文件分离能解决的问题。`-o /dev/null -w '%{http_code}'` 会让 `-w` 输出混进 body 文件，必须分开：`-o body -w '%{http_code}' > code 2> err` 三路分离。
### B ｜ Pitfalls（原 multi-model-review，逐条原话）
- **STATE/cache files in cron:** a script run by cron may not see drive letters like `H:` (cron cwd/env differs from an interactive shell). Store state/log under `HERMES_HOME` (e.g. `C:\Users\<user>\AppData\Local\hermes`), resolved via `os.environ.get("HERMES_HOME", ...)`. A state file on `H:` caused flip-detection to fail and a watchdog to spam "已恢复" every cycle.
  - **Sharp root-cause (observed):** if the state file is overwritten every cycle *without* persisting the timestamp (e.g. `open(STATE).write(cur+"#"+fails+"#"+reported)` clobbers a 4th `#timestamp` field), then a recovery-dampening window can never work — `last_recover` always reads 0, so every recovery reprints. Keep ONE canonical state format with a timestamp field written on BOTH the error and the OK branch, and read it back consistently.
  - **Suppression that actually worked:** user explicitly said "不要一直发" / "怎么还在发". Final fix = (a) delete the "已恢复" print entirely (user doesn't want it), (b) error branch prints only on flip (`reported != "ERR:"+cur`), (c) all state writes carry a `#<now>` timestamp. Continuous-down and continuous-up are both silent.
- **More GLM tokens ≠ usable:** user bought more GLM free tokens but calls still 429/empty. Free-tier **RPM (requests/min) is a separate wall from token balance** — topping up tokens did not raise RPM. Don't promise "now we can use GLM" just because tokens increased; still hit short-output + backoff + low-peak. (Paid GLM Coding Plan would raise concurrency, not the free tier.)
- **Flip-only reporting:** a monitor should print only on state *transition* (down→up, up→down), persisting last state in the state file. Continuous-down or continuous-up = silent.
- **Nous Portal wrong for GLM:** `inference-api.nousresearch.com/v1` returns 404 for `zai/glm-*`. Use `open.bigmodel.cn/api/paas/v4/chat/completions` direct (verified working 2026-08-16). `api.z.ai` ALSO 404s — do NOT use it.
- **Empty content ≠ failure to log:** when GLM/DS return empty, still write what you have and note the limit; don't present a failed call as success.
- **DS 返回"思考草稿"而非成品：用 finish_reason 判定，不要靠加/减 max_tokens 猜**: DeepSeek 把结论写进 `reasoning_content`、`content` 给空串或极短，是常态，所以必须 `content or reasoning_content`。但**这个兜底会把被截断的思考稿伪装成成品**：思考稿有小标题有表格、读起来像完整报告，只是结尾半句断掉。**判据要机械化，不靠肉眼**——`finish_reason != "stop"` 或 `completion_tokens >= max_tokens` → 判截断，改预算重跑。
  **预算按任务规模定，不存在一个通用数字**:
  - **短审计**（背景一句话、只问一句）推理只花几百 token，`max_tokens=700-900` 就够；给 2000+ 会让思维独吞预算、content 空。
  - **长背景包 + 多问分析**（prompt 约 4K token）实测推理 **9K–16K** token：`max_tokens=8000` 会被思维吃满、`content` 全空，必须给到 **32000** 才出成品（实测 in≈3.9K / reasoning≈9K / content≈5K / finish=stop）。
  若连续两次只拿到思维流，缩短 prompt 并明写"直接输出结论，不要写思考过程"。**别把思维流当失败空转重跑**——先读 reasoning 里是否已含全部结论，有就直接提取；也**别用长度判断质量**，截断稿很长但没用。
- **审计 prompt 必须逼出"命令级/逻辑级"红线才值**: 用户要的是"动手会不会崩/丢数据", 不是"写得不错"。prompt 明示"挑刺: 列出最高危的N条(带具体命令/路径/数据), 给红线+能否一次性搞定", 逼模型出可执行结论而非泛泛好评。本次迁移/监控/文件管理三次审计都靠这条拿到真坑(整目录scp崩/SSD挂丢记忆/smartctl无tty静默失败/排除vault过度保守)。
- **Kimi K2.6 temperature 硬限=1**: 传 0.3 直接 400 `invalid temperature: only 1 is allowed`。调用 Kimi 务必 `temperature=1` (本场实测首轮失败)。LongCat/DeepSeek 可 0.3, Kimi 不行 —— 分模型设 temp。详见 `references/longcat_qwen_vision_quirks.md`。
- **LongCat 截断重跑模式**: reasoning 模型结论在尾部, max_tokens 给足仍可能卡中段截断。首轮截断→重跑改 prompt 只要求缺失段 + 降 max_tokens 聚焦, 勿盲目加额度。content 空但 reasoning_content 有实质→直接当结论用。
- **端到端交叉审真能抓单模型漏的缺陷 (本场 evo v0.4 立项实证)**: 链路 搜集→LongCat全景→DeepSeek主审→写方案→Kimi代码二审+LongCat复审→修订。Kimi 独立抓伪技能/锁JSON损坏/命中注水; LongCat 独立抓阶段C-SMB破本地主权+阶段E收外部数据违不联网底线。二者交叉印证"单模型审会漏逻辑/底线冲突"。审方案 prompt 必须显式写"找逻辑漏洞+底线冲突", 不只问"有没有bug"。 cron runner 在 Windows 上 PATH 里没有 bash → `.sh`/`.bash` 直接报 "bash not found on PATH" 失败。改写成 Python(`subprocess` 调 ssh/scp), `script="name.py"` 即可。且 `script` 参数已相对 `scripts/` 目录, **不要再前缀 `scripts/`**(否则变成 `scripts/scripts/name.py` 找不到)。本次 timetrack 部署连踩这两坑: 先 `.sh` 失败, 改 `.py` 后又多写前缀路径, 重建 job 才通。
- **Do NOT mislabel paid vs free keys (user correction).** This user's `DEEPSEEK_API_KEY` is a **user-PAID / 充值 key** (bills their DeepSeek account balance, NOT free tier). GLM (`GLM_API_KEY`) is the **free** one. When reporting API behavior, say "DeepSeek paid key, direct calls" — never "DeepSeek free tier". The empty/429 on DeepSeek calls were proxy-flak (Clash inherited by the API client) or transient truncation, NOT a free-tier RPM wall. Free-tier RPM limits apply to GLM only.
- **Nous credits are separate:** routing GLM/DeepSeek through `hermes chat -m zai/glm-*` or `nous/...` spends Nous credits (reserved for Sonnet). Call GLM/DeepSeek **directly** (api.z.ai / api.deepseek.com) — that bills the user's own GLM free quota / DeepSeek paid balance, not Nous.
- **HuggingFace model downloads also inherit the proxy:** `transformers` library's `from_pretrained()` uses `requests`/`urllib` which pick up `HTTP_PROXY` env vars. On 3046 this routes through Clash and times out even though the network is fine. Fix: `unset HTTP_PROXY HTTPS_PROXY http_proxy https_proxy` before pip install / model download, or set `HF_ENDPOINT=https://hf-mirror.com` for the domestic mirror. Verify with `curl -sI https://huggingface.co` (DNS resolves = network is fine, it's the proxy path that breaks).
- **PyTorch CC 6.1 incompatibility (P620):** Quadro P620 is CUDA capability 6.1. PyTorch ≥2.1 requires CC 7.5+. Must use PyTorch 2.0.x (`torch==2.0.1+cu117`). Also PyTorch 2.0 doesn't support Python 3.12 — create a Python 3.11 venv: `python3.11 -m venv $HOME/.venvs/moondream`.
- **Ollama HTTP on low-VRAM GPU (P620 2GB):** Sustained batch inference crashes Ollama even with retry+rate-limit. The GPU simply runs out of VRAM under continuous load. Workarounds: (a) local PyTorch/llama-cpp-python inference, (b) limit Ollama with `OLLAMA_MAX_VRAM=1500000000`, (c) offload to a stronger GPU (RTX3060 6GB on the desktop). For 8000+ images, option (c) is most reliable.
- **P620 2GB VRAM 是本地推理硬瓶颈**: Quadro P620 只有 2GB 显存，跑 moondream 1B 推理（需 ~1.5GB VRAM）在批量场景下必然溢出。Ollama HTTP 持续推理 → 500 错误；transformers 本地推理 → 加载后推理OOM；llama-cpp-python → clip_model_path 多模态返回空（P620 不支持）。**3046 上做批量图片/视频推理不现实，应优先考虑台式机 RTX3060（6GB）或云端 API。**
- **情景/触发矩阵审查(2026-08-19 实测有效)**: 当交付物是"监控/告警/状态机"类的触发条件清单(如 S1-S14 时间情景), 必须让 GLM+DS 专门审 **覆盖完整性 + 互斥性**, 不要只审"代码对不对"。本次两模型抓出: ① 情景重叠(S2 running超预估 与 S3 pending超预估 边界不清, S4 临界与 S1 超时重复报) ② 遗漏维度(周期任务 next_due、依赖/阻塞等待外部态) ③ 重复触发(状态持续而非跃迁时每轮都报, 需 `last_report`/翻转检测去重) ④ 误报(正常空闲/睡眠被当异常)。审这类交付物时, prompt 要明示"找遗漏的情景、会重叠/重复报的触发、正常态误报", 不要只问"有没有bug"。
- **字段/依赖先于逻辑**: 检查器逻辑若引用账本里没定义的字段(如用 `created` 算超时但字段清单只列了 `due`), 会直接跑不起来。多模型审方案时一并审"逻辑引用的字段是否都在数据模型里"。
- **验证并发写勿同进程边写边读(2026-08-24 实测假阳性)**: 测 append-only 日志并发安全时, 若用 threading 同进程多线程边写边 open() 全文件读计数, 会报"全部行损坏"假阳性(读到半行). 真验法: 先 cp 备份重置干净基底(少量行)→单进程顺序写 N 条→独立进程再 open() 逐行 json.loads 校验. 本次 evo_events.py 双锁(threading+flock)+fsync 修复后, 独立进程验 33 行零损坏, 确认功能 OK, 假阳性排除. 教训: 并发安全验证必须读写分离到不同进程, 否则测试脚本自身制造损坏假象.
- **并发追加双锁模式(2026-08-24 沉淀)**: 纯本地 JSONL 事件日志抗"同进程多线程+跨进程(cron/主进程)"并发写, 仅 fcntl.flock 不够(它只防跨进程, 同进程多线程共享 fd 时第二线程仍能拿同把锁). 正确做法: threading.Lock() 包住 open()+fcntl.flock(LOCK_EX)+write+flush+os.fsync+flock(UNLOCK). 另: 单文件无限增长需 50M 轮转(rename 成 .1); log() 接口应带 run_id 关联轨迹; replay 加 limit 防内存暴涨; 损坏行 continue 前先记录便于排错.
### B ｜ 审「规则/纪律/文档集合」内部矛盾：可行配方与两个陷阱

审一份多条目规则库（skill 的纪律条目、风格指南、策略文件）有没有自相矛盾时，**关键词共现类机械检测必然产出垃圾**。曾用「同主题关键词正则配对」查冲突，输出 334 对候选——全是假的：关键词（「静默」「证据」「确认」）在几乎每条里都出现，因为多数条目是在声明本条不适用。

**可行配方：多模型语义审 + 逐条回源核验。**

1. **先跑机械统计**（条数/字数/交叉引用/孤立条目/编号连续性）——这些是**客观量**，可直接进裁决。注意孤立条目数（无任何交叉引用 = 不认识其他规则存在）和编号连续性是真实缺陷信号。
2. **再派多模型做语义审**，prompt 里**必须显式列出伪冲突排除项**，否则拿回一堆「主题相关但并不矛盾」的噪音：
   - 只是主题相关不矛盾（两条都要求给证据）
   - 管不同轴/不同场景（**「不主动推送」vs「回复内必须带证据」可以同时成立**）
   - 抽象张力但具体执行不冲突
   - 一条是另一条的细化或例外 → 判**层级关系，非冲突**
   - 要求模型**逐条说明排除理由**，这样假阳性也可复核。
3. **回源核验每一条指控**：grep 原文确认那句真存在、且真的矛盾。**三方一致不等于属实**——模型可能一致地读着旧版本，或一致地误读一句。
4. 只改**真冲突**，并在条目内写明它与哪条冲突、怎么共存；伪冲突只在结论里说明理由，不改文件。

**陷阱一：自己的核验判据会假阴性，别用它否定外部指控。**
判据写 `kw in body(n)` 时，中英文/全半角/空格差异就会漏判——先后用「不用列变量」vs 原文「不列变量」、「8个以上标签」vs 原文「8 个以上标签」否掉过两次指控，其中一次是错否（三模型一致指出的重复编号是真的）。
→ **判据与外部结论冲突时，先怀疑判据**：打印命中行原文而不是 bool；拿不准就 `grep -n` 看真实文本，别用字符串精确匹配定性。
→ 这与「负样本最关键」同源：判据型代码的错误不会崩溃，它会**安静地给出错误的安全感**。

**陷阱二：在正文下加「限定段」不改正文，等于没修。**
补冲突时若只在条目末尾追加「本条应服从 X」，只读前半段的人仍会被原句误导。**冲突条目的原句本身必须改**，末尾限定段只作补充说明。

### B ｜ 2026-08-19 会话关键坑（本次踩过, 已修进模板）
- **GLM 免费档 content 常在 `reasoning_content`**: 读取务必 `content or reasoning_content`, 否则拿到空串 → 重试空转 → 超时(本次 300s 全耗在空重试)。`pipeline_template.py` 已修正为双字段兜底。
- **模板 GLM 端点已过期**: 原 `api.z.ai/api/paas/v4/...` 实测 404。已改 `open.bigmodel.cn/api/paas/v4/chat/completions`(与 cookbook 一致)。
- 用户说"调用多模型审核技能"时, **先 `skill_view` 加载本技能**, 不要手搓脚本 —— 本技能自带模板与 cookbook, 手搓易漏上述坑。
- 慢≠卡死: 免费档 RPM/输出限制会让长审查返回空, 靠短 prompt + 双字段 + 重试解决, 不是网络断了。
- **key 探测姿势**: `.env` 里 key 用 `grep` 可能漏(行尾/编码), 用 python 正则 `^KEY\s*=\s*(.+)` 才抓得到。本次用户说"已配置"但 grep 搜空, 实际 key 在(长度49/35)。
### B ｜ 实操铁律里的坑（本会话用户反复纠正, 已固化）
- **.env key 引号坑(实测)**: `SILICONFLOW_API_KEY='sk-xxx'` 带单引号 → 调 API 401。读取须 `v.strip("'").strip('"')` 去首尾引号(本次已修, 见 `references/siliconflow-strategy.md`)。其他 key 同理排查。
- **SF 兜底已内化**: `pipeline_template.py` 的 glm() 6次失败自动调 sf_fallback() 走 SiliconFlow Qwen3.5-35B-A3B, 实跑验证通。改模板勿删此兜底。
- **不要反复让用户手动执行**: 用户原话"不要老是让我来弄"。能自动化(脚本/SSH公钥免密/API)就自己跑完, 只把"必须用户物理操作"那一步(如插显示器/粘公钥)留给他且一次说清。反复让他贴命令到终端 = 失败。
- **审核类 prompt 必须要求模型补出「你没列到的类别」**(本场实测有效): 只把自己列的检查清单给模型, 模型就在**你的盲区里**作答, 拿回来的只是你已想到的东西。prompt 里附上预设清单后明写「还要列出我没提到的类别——这部分才是本次审核的原价值」。本场靠这条从 4 个模型拿回 6 个预设清单外的缺陷维度(跨文件重复且措辞漂移 / 待办与事实同槽 / 否定性事实缺替代指针 / 能力与权限错位 / 悬置状态未闭环 / 画像即授权)。
- **单一模型的具体断言必须回源核验, 长输出 ≠ 高可信**: 本场分析最长最细(13.8KB)的那份报告里夹着**假阳性**——它断言文件末两条粘连、清理时可能被一起删; 回源一看分隔符就在那儿, 结论作废。**细节越多越容易夹带假阳性。** 综合前拿原始文件逐条验, 并把「被核验推翻的模型结论」单列一节告诉用户, 不要静默丢掉。
- **回答语言错配 = 降权**: 要求简体中文却用英文作答、并把原文**译成英文**再分析的模型, 中文语感损失且结论基于译文——标低权重, 明确告诉用户不要拿它的逐条清单当行动依据。
- **阵容里某模型调用失败, 本身可能就是审核证据**: 本场某模型 429 挂掉, 而被审文本里同时写着「多模型可用: …该模型…」与「该模型欠费」——**失败把这条矛盾当场证明了**。别把"阵容缺一个"只当运气不好, 先看它是不是在证明被审内容自相矛盾。
