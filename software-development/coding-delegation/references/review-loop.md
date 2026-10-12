# 多模型审核 + 相互学习闭环

> 来源：合并 `pi-hermes-review-loop` + `coding-agent-tooling` 的多模型审段 +
> `external-model-coding` 的双模型交叉段（2026-09-26）。

## 一、相互学习闭环（Pi ↔ Hermes）

用户 2026-08-29 明确意图："研究 pi，相互学习，更好为我工作"。
**Pi 不是一次性工具，而是与 Hermes 互补的长期编码副手，能力随任务真实增长。**

### 闭环 5 步（每轮任务必走）

1. **派活**：`pi --provider <p> --model <m> -p "<task，要求写到文件而非只打印>"`
   - 关键：让 Pi **写文件**（`-p "write to /path/x.py"`），不要只打印——
     打印会被 `head` 截断丢关键逻辑（实测踩过：截掉了 255 重试逻辑）。
   - 给足 `timeout`（90s–300s）。
2. **Hermes 审**：读 Pi 产出的真实文件，拿去多模型交叉审。
3. **挑缺陷**：不只夸，要挑真 bug（计数逻辑错、不支持的格式列进扩展名、正则过宽误匹配、
   错误码没区分等）。
4. **回写 `~/.pi/agent/AGENTS.md`**：把缺陷+教训写进「踩坑记录」段
   （格式：`日期: 问题→修复→教训`）。**Pi 下次启动自动读这份指令，规避同类错。**
5. **让 Pi 自修**：把审出的缺陷作为新 prompt 喂回 Pi，形成「审→改」子闭环。
   改完**读码验证**它真改对（不轻信自述）。

### 架构（互补，非替代）

- **Pi**：专注代码读写改（read/bash/edit/write 工具）。
- **Hermes**：调度、跨机、真相源、多模型交叉审、把坑回写 Pi 的 AGENTS.md。

### ⚠️ Pi 是无主动回调的批处理模式

`pi -p "..."` 跑完返回文本即退出，**不会主动通知 Hermes**。
所以闭环由 **Hermes 驱动**：写 prompt → Pi 跑 → 读输出 → 审 → 再写 prompt。
要求 Hermes **主动 poll / 读产出**，不能等 Pi 来找。

### 红线

- 不把 Pi 当通用 agent 用（它只 coding，无记忆/调度）。
- **不省略「回写 AGENTS.md」这步**——那是能力增长的载体，漏了 Pi 下次还犯。
- 不轻信 Pi 自述，必实跑验证。
- **绝不编辑 Pi 的 AGENTS.md / models.json / bundle 来加功能或省 token**（用户两次叫停
  "Pi 不要动"）。token 节省走 Hermes 侧或派活 prompt 层。
  **回写「踩坑记录」段是唯一例外**（用户授权的学习载体，只记缺陷教训，不改行为框架）。

### 实测收益

- Pi 写 `exif_inject.py` → Hermes 审出 3 缺陷 → 回写 AGENTS.md → Pi 修✓
- Pi 写 `fileutil.py` + 17 个 unittest 全过
- Pi 独立审 relay 脚本挑出 12 处问题（含 Hermes 漏掉的 P0 级「测试 SSH 无限挂起」）
- 证明审能力可用，应纳入常态

---

## 二、多模型交叉审核阵容（2026-09-03 实战确认）

用户明确要求：**用 DS + Kimi 做代码/方案审核，不要用 LongCat 当主力**。

| 角色 | 模型 | 看什么 |
|---|---|---|
| **主审** | DeepSeek | 技术可行性、架构缺陷、遗漏风险 |
| **二审** | Kimi | 实操落地性、场景适配、与现有体系整合 |
| **三审/兜底** | LongCat（可选） | 仅在 DS/Kimi 超时或 429 时 |

**严禁**：跳过 DS/Kimi 直接用 LongCat 当主力审核。

### 调用顺序

```bash
pi --provider deepseek --model deepseek-chat --print "prompt"   # 主审
pi --provider kimi --model kimi-k2.7-code --print "prompt"       # 二审
```

**注意**：
- DeepSeek / Kimi 都有 RPM 限流，429 时等 1-2 秒重试或切模型。
- 超时（>120s）切 LongCat，但需标注"LongCat 替代审核，可信度低于 DS/Kimi"。
- Pi 的 `--timeout` 参数不存在，用 terminal timeout 控制。
- **Kimi 必须 `temperature=1`**，否则 400。

### 完整阵容（2026-08-31 用户铁律）

- **主审必须是 DeepSeek 或 Kimi**，免费模型不顶主审。
  用户原话："应 deepseek 或者 kimi 主审，其他二审三审随意"。
- 免费三模型（LongCat / Step-3.7-Flash / Laguna-S-2.1）**只作交叉/兜底**。
- 模型名精确：DeepSeek → `deepseek-chat`；Kimi → `kimi-k2.6`/`kimi-k2.7-code`（
  直连 api.moonshot.cn，限 3RPM）；GLM → `glm-5.2`。
- **空响应 = 不可用**：某模型返回空/429 → 标记失败，不伪造意见，不重复烧额度。
- **DS 审计读 `reasoning_content`**：DeepSeek 有时把结论放 reasoning_content 而非 content，
  必须读 `content or reasoning_content`。
- **审计 prompt 逼出红线**：要"动手会不会崩/丢数据"，不要"写得不错"。
  明确要最高危 N 条 + 具体命令/路径 + 能否一次性搞定。

---

## 三、双模型交叉验证·实例

- **方案层（自驱循环）**：Hermes 起草 → GLM 审 → GLM 补漏洞"心跳须校验真实进展(防假自驱)" → 定稿。
- **方案层（路由固件）**：AX6S 刷 OpenWrt 方案 Hermes 起草 → GLM 审 →
  GLM 补"刷前必须备份原厂固件"（原漏项）→ 定稿。
  **教训：单模型起草必有盲点，交叉审补致命漏项。**
- **代码层**：GLM 写初稿 → DS 审查挑 bug → DS 修正/重出 → Hermes 拼装实跑。
- **铁律**：任何全面落地方案须 ≥2 模型交叉再定稿，禁单模型拍板。

---

## 四、LongCat 额度消耗策略

用户 2026-08-29 指示：LongCat 资源包 **2026-09-22 到期作废** → 过期前主动让 Pi 多跑真实任务
消耗，既练能力又不浪费。

- 3500 万 token 量级，可猛练：写工具脚本 / 审现有脚本 / 写带 unittest 的模块。
- 实测 Pi 用 LongCat 能产出**可跑通**代码（如 17 个 unittest 全过）。
- 优先级：有真实需求先满足需求；纯练手用文件/图片工具类小任务。
