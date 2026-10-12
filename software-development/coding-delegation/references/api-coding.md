# API 直调写码流水线（GLM 写 → DS 审 → 拼装实跑）

> 来源：原 `external-model-coding` 技能主体（合并 `supervisor-coding` + `submodel-codegen`）。
> 适用：只需生成**独立代码片段**、不需动仓库时——比派 CLI agent 更便宜更可控。

## 适用边界

- 任何需可靠生产脚本的任务（cron 周期执行、动文件系统、算数据、联网抓取）
- **小脚本（<50 行、纯标准库）**可自己手写（如 `add_weekly.py`、plot、推送端）
- **大/复杂/长脚本必须强模型写**，宁可拆函数分段也不要单次生成长脚本

## 固定分工

| 角色 | 干什么 |
|---|---|
| **主模型（Hermes）** | 写需求规格 → 拼装片段 → **实跑验证** |
| **GLM-4-flash** | 写初稿（短脚本稳，长脚本会空回/截断） |
| **DeepSeek** | 审查+修正：挑 bug、修逻辑、兜底 |

方案层可 Hermes 起草 + GLM 审；**代码层 GLM 写 + DS 审**。

> ⚠️ **2026-09-26 现状**：GLM 付费档（glm-5.2/4.6）余额不足，只剩免费档 `glm-4-flash`（仅短输出）。
> 原"GLM 写初稿"仍可行，**但必须配合下面「拆函数分段」的手法**（每段 `max_tokens` 600–900）。
> 若 GLM 彻底不可用，直接改用 **DeepSeek 写 + DeepSeek 审**（同模型不同轮次，
> 效果弱于双模型交叉，需更严的实跑验证）。

## 已验证流水线

1. **Hermes 写需求规格**：每个脚本的输入/输出/静默要求/防假自驱校验点写清楚，当 prompt 给模型。
   子模型**只执行规格，不设计**。
2. **GLM 写初稿**：直连 api.z.ai（`GLM_API_KEY`）。
3. **DeepSeek 审 + 修**：直连 api.deepseek.com（`DEEPSEEK_API_KEY`），审查初稿挑 bug。
   - 实坑：DS 审出过 GLM 初稿 **13 个 bug**（致命：把中文"周一"当 int 用必崩、逾期逻辑错、日志类型错比较）。
4. **Hermes 拼装 + 实跑验证**：写最终版（绕开转义坑用 `write_file`，勿用 `terminal -c` 拼接），
   跑一遍确认 exit 0 + 产物正确，才交付/建 cron。
5. **双模型验证纪律**：方案/架构须 Hermes+DS 或 DS+GLM 交叉定稿，禁单模型拍板。

## 长脚本防截断解法（实证）

**把脚本拆成小函数，每个单独让 DS 写短片段（`max_tokens` 600–900），Hermes 再拼装。**

- 实证：`heartbeat_check.py` 拆成 `parse_frequency` / `next_execution` / `parse_heartbeat` / `main`
  四段分别生成，全跑通。
- 此法同时破解 GLM 空回 + DS 截断，并隔离 bug。

## 关键坑（全部实踩过）

- **GLM 初稿不可直接跑**：13 bug，必须 DS 兜底审。
- **DS 修正版 token 截断**：长脚本单次生成残缺（~1800 token 就断，导致 if 后缺块、IndentationError）。
- **拼装键名/helper 缺失 + 转义坑**：用 `write_file` 直接写最终版，**勿用 `terminal -c` 拼接**
  （全角括号/反引号/单引号触发 bash 转义，字符串里 `\n` 被当成真换行）。
- **DS 代码块标记未剥净**：有时没被正则剥掉 →
  提取后做 `.replace('```python','').replace('```','').strip()`。
- **调用模型用 `requests` + `proxies={'http':None,'https':None}`**：国内 API 直连，
  勿走 Clash 7890（否则慢/超时/被拦）。
- **GLM 模型选择**：glm-4.7-flash 长输出空回；glm-4.6-flash 403 限流；**glm-4-flash 最稳**。
- **Windows 路径 join**：无尾分隔符时会把 `dir_` 当目录 → 用正规尾分隔符 +
  `os.makedirs(exist_ok=True)`。
- **静默纪律**：生产脚本正常态零输出，仅写日志/文件；仅异常才 print 一句。

详细行为表 + 装配坑 → `references/model-quirks.md`（原 `model_quirks.md` 下划线命名已改连字符）

## 验收纪律（不可省）

```python
import subprocess
rr = subprocess.run(['python','script.py'], capture_output=True, text=True, timeout=30)
print(rr.returncode, rr.stdout[:300], rr.stderr[:300])
```

干净 exit 0 + 预期日志行 = 通过。任何 traceback = 修好再交付。
cron 目标脚本还要确认：**只写本地日志、正常路径不打印任何东西**。

**不拿"写完"当"能用"**；截断/崩了就补跑或拆段重生成。

## API 配方

见 `references/api-recipes.py` —— 含 `call_glm` / `call_ds` / `extract_code`。

## 模型池 & 可用性（2026-08-15 实测，国内直连不锁区）

- **HY3:free（Nous）**：表象免费（BYOK 走 Nous 额度，非真免单）。
  **风险：Nous 收免费档即断**，需备份池。
- **Gemini API 实测死路**：Google 锁区（`User location is not supported`），
  中国账号+代理都绕不过 → **别走 Gemini 路线**。
- **硅基流动 SiliconFlow（国内直连可用）**：一个 key 通吃几十模型。
  付费档廉价且强：DeepSeek-V4-Flash（输出¥2/M）、Qwen3.5-397B（¥7.2/M）、GLM-5.2（¥6/M）、
  Kimi-K2.7-Code。余额 0 时主力档 402 → 充 ¥10 即全开。key 存 `SILICONFLOW_API_KEY`。
- **Fallback 链**：HY3:free → 腾讯官方 HY3 → 硅基 DeepSeek-V4 → 硅基 Qwen397B → 硅基 GLM-52。

## 脚本审计/清理·范围铁律（防误删软件本体）

- Hermes 软件包本体目录（`hermes-agent/`，3900+ 个 .py）靠 `import` 关联，
  **文件名字符串匹配抓不到引用** → 任何"无引用=孤儿"扫描都会误判它们为可删。
- 审计用户自建脚本时**硬排除**：`hermes-agent/`、`venv/`、`node_modules/`、
  `ds_harness/`、`acvenv2/`、`skills/`、`optional-skills/`、`__pycache__/`。
- 孤儿判定：无文件间引用 + 未被 schtasks/定时任务调用 + 超 7 天未改。
  清理前移到 `_trash_<日期>/` 备份（可反悔），不永久删；删除动作等用户拍板。

## 自演化引擎配方

见 `references/agent_self_evolution_engine.md`：事件驱动→蒸馏成原则(Qwen)+验证(GLM 异架构)
→原则库检索→反馈闭环；防反向污染三道闸（黄金样本回归/必填校验/验证失败拒入库）。
参考实现 `$HOME/evolve.py`。

## 用户风格（嵌入）

- 用户说"过程我不专业，我就要结果" —— **方案经他拍板后，一路建完再报结果**，
  不在子步骤反复问确认。
- 用户喜欢 Hermes"不想被取代的机灵劲" —— **机灵劲保留在沟通/主动性，不体现在硬扛代码**；
  编程能力必须靠强模型补。
- 用户对"解释价格/技术"要求**给具体数字与真实机制**，勿空泛。
