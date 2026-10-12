---
name: safe-file-organization
description: Use when 删旧文件/归档/清理目录：整理磁盘、防误删（rm 改 trash）。
---

# 安全清理（文件整理 · 去重 · 删除安全 · 脚本审计）

四个触发面共用同一条脊柱：**只读清点 → 报告不删 → 用户拍板 → 执行并复核**。

| 用户在做什么 | 去哪里 |
|---|---|
| 整理乱目录、归类、日期分桶、"不能变垃圾场" | §1 §2 |
| 查重复文件（"看看有重复的么""移到X那边去"） | §3 |
| 让 `rm` 不再破坏性、"防止误删"、"删了能找回" | §4 |
| 清理无用脚本 / 审计项目 / 全面审查编程项目 | §5 |
| 归档节奏、Obsidian/LLM-Wiki/知识库、NAS 规划 | §1 + `references/archive-hygiene-two-zones.md` |
| 照片库、知识库从程序目录里分出来 | §6 |

## §0 铁律（非协商，先读这段）

1. **只读清点先行。** 未摸清有什么之前，绝不移动/删除：`du -sh`、`find ... -printf`、文件类型直方图、总数。
   目录里常混着：个人档案、工程文件（dwg/pdf/rps/skp）、社交导出（Telegram/微信）、相机胶卷、以及**敏感不可替代**的项（见下）。
2. **没有明确拍板就不删。** 尤其是敏感/不可替代数据。重复文件**只报告**，让用户选"两份都留（冗余）"还是"删一份"。拿不准就留。
3. **分批批准，然后执行。** 方案分 **A**（轻清理：空壳、失效 .lnk）/ **B**（分类：散落文件归位、相机胶卷按日期）/ **C**（深度：知识库 / Obsidian / RAG）。逐批取得许可；**一批批准后，就不要再逐个文件问**。
4. **深度工作（C）可以延后。** 用户说"先A+B，C到时候我提"时，在 A+B 阶段把完整清点做完，别重复发现。
5. **复核，不假设。** 移动后：数源/数目标文件数、确认源根已空、查嵌套目录 bug、**回读真实路径**（不是我以为的路径）。
6. **不盲目装软件。** 先勘察已有工具；能用现成的就别自己造。
7. **删除用"移到 trash/备份目录"而不是永久删**（见 §4、§5），可反悔。

### 🔴 保护名单（硬隔离，永不删、永不出本地）

- **王浩纪念照片**（已故亲人照片，22G+）、**基因/体检原始数据** —— **只做中性整理**（分类 / 冷备校验），
  **NEVER delete, NEVER send to cloud models**。
- 默认规则：家庭/健康/基因档案 = **hard-isolated**。
- **但用户可逐批放行**："CC_Switch/VAULT 这批可以上云"只放宽**那一批**。
  **每一批都要确认它属于哪一类**——别假设全局适用默认规则，也别假设放行是全局的。

> 同一份保护规则在 4 个源技能里各有一版措辞（`archive-hygiene` 版、`safe-file-organization` 版等），
> **两版都保留**：`references/archive-hygiene-two-zones.md` 是 `archive-hygiene` 的逐字原文，
> 上面这段是本技能正文版。**不要只留一版**（2026-09-27 合并时踩过：把"措辞不同"当成"同一句话说两遍"会丢信号）。

## §1 归档卫生：两区原则

**把"工作/暂存区"和"归档区"分开，绝不在归档区里做脏活。**
- **暂存区**（`/data/fast/_incoming/` 之类）：外部文件先落这儿（微信/Telegram/相机/下载/项目导出）。
- **处理在暂存区**：整理 → md5 去重 → 分类。
- **归档区**（`/data/vault/<主题>/`）：只放处理完、去过重、分好类的文件。
- 这样归档区**由构造保证干净**，"垃圾场"不可能出现。

**Standing pipeline（用户 2026-08-22 定义）**：外部文件 → `_incoming/{微信,Telegram,相机,其他}` → 在 fast 里清点/去重/分类
→ 移进 `/data/vault/<主题>/`；**fast = 工作台，vault = 归档**；季度复盘（90d cron，**只报告不自动删**，
job id `a8ef9e6d20aa`，下次 2026-11-20）；长期目标：NAS 接管大文件冷存储，3046 vault（1.4T）是过渡。
→ 详见 `references/standing-pipeline.md`

## §2 整理工作流

清点（只读）→ 识别（空壳/重复树/散落文件/属主不匹配）→ 提 **A/B/C** 方案（轻清理 / 分类 / 深度）+ 风险标签 →
等批准 → 执行该批并用真实输出复核 → 去重只报告 → 结构变了再更新进度笔记/记忆。

**A/B/C 的完整定义与逐步要求 → `references/workflow-abc.md`**

## §3 去重顺序（用户纠正过：2026-08-26，2026-09-02 强化）

**不要一上来就全量 MD5 扫描。** 慢盘（HDD）+ 几千文件时 `find ... -exec md5sum` 会在前台 180s 超时、白耗用户时间。
用户原话："先对文件名是不是一样的，再对哈希数是不是比较合理"。**从便宜到贵**：

1. **文件名比对**（纯字符串，秒级）：两边 `find ... -printf "%f\n" | sort -u`，`comm -12` 取交集。
   手机原图（`IMG_20240308_172939.jpg`）与重命名过的归档几乎不会同名 → **期望 0 命中，这本身就是快速信号**。
2. **文件大小比对**（只 stat，快）：提取 `size\tpath`，`sort -n`，`join` on size。
   若 size 集合**零交集**，内容不可能相同（同字节 ⇒ 同大小）→ **可以不哈希就高置信度报告"无重复"**。
3. **只对 size 匹配上的候选算 SHA256**（唯一值得哈希的那些）。或者做统计性验证：**随机抽 5 个文件**哈希，
   拿去 grep 另一棵树的完整哈希表——便宜且能抓到明显情况。

> 实测：把 180s 超时变成 **2 秒结论**（Camera 6351 张 vs vault 4791 张：文件名零交集、size 零交集 ⇒ 不重复，
> 并用 5 文件随机抽样复核）。

## §4 删除安全化（`rm` → trash）

三个 Python3 工具（仅标准库，`#!/usr/bin/env python3` 以便 cron 的最小 PATH 能跑）：

| 工具 | 职责 |
|---|---|
| `safe-rm` | 命中保护名单 → 打印 `PROTECTED: 文件受保护，跳过` 并 exit 1；否则移到 `~/.trash/YYYY-MM-DD/<basename>.<YYYYmmdd-HHMMSS>`（冲突加 `.N`），追加 `orig,deleted_at,size` 到 `~/.trash/log.csv`，写 `<file>.meta` 旁车文件 |
| `trash-list` | 输出 删除时间/大小/原路径 表 + 合计；`--json` 供自动化 |
| `trash-empty` | 只列超过 `--days 30` 的条目；**只有加 `--force` 才真删** |

装到 `/usr/local/bin`（root）**并且** `~/.local/bin`；`*.meta` 旁车文件让修复脚本能重建被截断的 `log.csv` 丢的行。

**必须记住的规则**（完整版 → `references/safe-rm-trash-design.md`）：
**验证**：`~/.hermes/scripts/safe-rm-selftest.sh` 跑全矩阵（⚠️ 2026-09-27 实测：该脚本曾被移进 orphan 归档、指针失效，已复原；**跑前确认 `~/.trash` 无真实数据**——T16 会 `--force`）——受保护的 `.env`/`.bashrc`/`*.md`/`/data/vault/`（exit 1）、普通文件与 `-rf` 目录被 trash（exit 0）、`-f` 不存在的文件（exit 0）、`--list-protected`、`trash-list`、`trash-empty` 干跑后再 `--force`。

## §5 用户自建脚本审计

（排除范围、审计流程、常见 bug 全文 → `references/script-audit-rules.md`）

**触发**：清理无用脚本、审计项目、全面审查编程项目、找出会跑偏/失效脚本，或用户抱怨"脚本太多没用"。

### ⚠️ 致命陷阱（已踩坑，必读）
`hermes-agent/` 下 3900+ 个 `.py` 是 Hermes **软件本体**（包/tests/plugins），**不是用户写的，绝对不能清**。
它们靠 Python `import` 关联，非文件名引用 → 用"文件名互搜"判定会**把全部误判成孤儿**。
首次审计若全量扫描会列出 `hermes_cli/*` `acp_adapter/*` `tests/*` `plugins/*` 为"可删"——**错，会删崩赫米**。

**验证**：清理后确认 trash 文件数、原位置已空；月度审计 cron 正常态零输出，仅新孤儿才报告且不删。
→ 完整原文 `references/script-audit-rules.md`

## §6 照片库与知识库

- **照片库**（年/事件树 + `.meta.json` 云/本地标记，EXIF 年归档；红线：王浩纪念照片不得并入开放树）
  → `references/photo-library-structure.md`、`references/photo_library.md`
- **知识库提取**（把 Obsidian vault / `wiki/` 从程序目录里分出来；`node_modules`/`*.exe` 不是"资料"）
  → `references/knowledge-base-extraction.md`、`references/knowledge_base_smb.md`
- **远程机器清理标准流程** → `references/remote-cleanup-workflow.md`

## Pitfalls

- **扫「杂乱的目录」前先分两类：缓存类 vs 凭据类 —— 而用户往往只记得前者。** 用户说「根目录一堆散落文件，扫一下」时，
  第一直觉是「都是临时产物，大的先删」。实测一次扫描里，**占体积 99% 的是两天前留下的全量备份包**（真占地方），
  而**真正危险的是那堆看起来像垃圾的小文件**：`*.yaml` 订阅配置正在被看门狗脚本逐行引用，
  `.env` / `.bashrc` / `.gitconfig` / `config.yaml` / `.claude.json` 是活配置。
  **判据（动手前必跑）**：对每个候选，`grep -rl '<文件名>' <常驻脚本目录> <cron配置> <系统服务目录>`，
  **命中就归「凭据/活配置」，永不进入任何删除或搬移批次**。
  ⚠️ **凭据类文件名不带特征**：它们叫 `mysub.yaml` / `mihomo_config.yaml` / `config.yaml`，
  没有 `.bak`/`.tmp` 后缀，靠命名规则筛不出来。**只能靠「有没有人在读它」。**
- **清单里的「零字节文件」与「体积大头」是两回事，按用户问的维度答。** 用户问「这些都是啥、这么大？」
  答的是体积分布；问「散落审稿输出」答的是用途。**一次扫描要同时给两列：分类（用途）+ 合计体积**，
  否则用户以为「大文件才是问题」，实际大文件往往是唯一该保留的（完整备份），
  而体积可忽略的那几十 KB 才是他真正想清的。
- **搬运到归档盘时：类别白名单要去重，并在落点写 README。** 实测一批文件里 png 同时匹配两个类别（`nb_*.png` 既像房产数据又是OCR 切片），
  先落进 A、B 目录留空，需二次归位——**同一文件被两条规则命中时，明确指定归属或让后一条跳过已搬的，别靠事后补**。
  搬完在落点写一份 `README.md`：每类为什么搬、哪些没搬（配置/凭据）、怎么恢复。移动比复制省心，
  但**半年后没人知道东西去哪了**。落点优先用归档盘上已有的惯例目录（如 vault 的 `HermesBackups/`）而不是新造结构。
- 🚨 **「移到 trash」在 trash 与原目录同分区时并不腾出空间。** `safe-rm` 返回 rc=0 只代表
  「搬走了」，`df` 可能纹丝不动——它只是把 3G 从一个目录挪到同��个盘上的另一个目录。
  **给用户选项时必须把这条写进选项本身**（「移到 trash（可反悔，但不释放空间）」），
  不能执行完才补充——用户选「可反悔」时的合理预期是**两样都要**。
  真要「可反悔+腾地方」，得让 trash 落在**另一个分区/挂载点**。
  **清理后必须 `df -h` 实测并把数字报出来**，别拿 rc=0当「腾出空间了」。
- 🚨 **真要腾空间：搬到另一个挂载点 + 原位置留软链接，`mv` 不是 `cp`。**
  同分区移动（§4 的 trash、跨目录归档）永远不释放空间；必须是**跨文件系统**才有效。
  先确认目标在另一块盘上（`df -h /data/vault /` 两行 mount 点不同才算），再用
  `mv <src> <dst> && ln -s <dst> <src>`：路径不变 → 程序/脚本/定时任务照常跑，
  数据落到另一块盘 → 根分区释放。**别用 `cp`：跨盘 `cp` 后再 `rm` 源，中间态占双份空间，
  且中途失败会留下两份不一致的副本。**
  **搬完必须校验再汇报**：大文件比 checksum（`sha256sum <path> | cut -c1-32`，走软链接也能校验），
  然后 `ls -ld` 确认都是 `lrwxrwxrwx`、目标盘 `df` 涨了、源盘 `df` 降了。
  **可搬/不可搬要按「是不是活跃运行时」分**，别按体积挑：备份 zip、历史快照、旧技能库快照 = 纯存档可搬；
  会话数据库、正在跑的 runtime 目录、工具链目录（playwright 浏览器、node、venv）搬了等于换路径重装，
  风险远大于收益——**先给用户「零风险可搬」那一档，运行时那几G单独起一轮、停服务做**。
  同理，「装依赖顺手降级了某个包」这类副作用要主动报：搬走 719M 但根分区只多出 1G，
  就是因为同期 pip 装包占掉了差额，不解释会让用户以为搬运没生效。
- 🚨 **磁盘紧时先按「机械盘 vs SSD」分家，再决定搬不搬。** `lsblk -o NAME,ROTA,MOUNTPOINT`：
  `ROTA=1` 是机械盘。运行时本体（Python venv、Node、浏览器二进制、正在写的 SQLite 会话库）
  搬到机械盘 = SSD→HDD 降级，每次启动/每次读写走寻道；数据库还多一个「那块盘挂了就读不到」的风险，
  而且测速会骗人——`dd` 的顺序写/4K 随机写在 fdatasync 开销主导下可能 HDD 反而更快，
  **真正差距在寻道延迟，dd 测不出来**。所以判据不是数字，是「这东西是不是活跃运行时」。
  给用户选项时按「零风险可搬（备份 zip / 历史快照 / 旧日志快照）」和「运行时那几 G（需停服务）」分两档报。
- 🚨 **清理系统日志前，MUST 先定位刷屏源。** 日志大小是症状，重复报错才是病因；
  不找到源就清，几小时后重新写满。判据：单个已轮转日志里同一 tag 超过百万行 = 该源在刷屏。
  定位命令：`head -3000000 /var/log/syslog.1 | awk '{print $5}' | sed 's/\[[0-9]*\]:*//' | sort | uniq -c | sort -rn | head -12`
  （文件可能 1G+，必须只 head 前几百万行，不能直接 sort 全文）。
  两类根因修法不同：**内核 PCIe AER / Correctable error** 是硬件信号劣化
  （`lspci -nn -s <bus>` 看挂在哪个设备下），日志静音只是治标；**服务崩溃循环**
  （`Main process exited ... restart counter is at N`，N 上万 = 无限重启）是软件问题。
- 🚨 **删已轮转的 `.log.N` 用 `truncate -s 0`，不要 `rm`。** rsyslog 和 logrotate 都**期望文件存在**，
  rm 掉会让轮转链断、inode 变化。且要**先把特征统计存到归档盘**（AER 类型分布、崩溃循环 TOP10、
  非噪音的独特错误），删完就没了。持久化上限，否则几天后重新写满：
  logrotate 配置**默认只有 `rotate 4`（份数）没有 `size`**——所以单个文件能长到 GB 级，
  必须补 `size 1G` / `maxsize 1G`；journald 要写 `/etc/systemd/journald.conf.d/size-limit.conf`
  的 `SystemMaxUse=`。改前先 `cp <配置> <配置>.bak-<日期>`。
- 🚨 **判断一个 Python 包能不能删，MUST 查依赖图，只 grep 应用代码会漏。**
  `grep -rl '<包名>' .../site-packages/*.dist-info/METADATA`——包 A 可能只是包 B 的依赖，
  而 B 自己 grep 不到任何引用。删包一律走 `pip uninstall`（让 pip 做依赖检查），
  不要手删 site-packages 目录。装完新包 MUST 跑 `pip check` 捕获安装过程降级的已有依赖，
  并主动把降级报给用户。
- 🚨 **判断 `.env` 里某行能不能删，MUST 实测引用数，不能看它在哪个注释块下面。**
  同文件相邻 ≠ 同归属：一个「装 X 的配置块」下面常混着 X 根本不用的通用设置
  （镜像源 env、公共 API key），而通用设置往往被其他脚本引用。
  判据：`grep -rl '<VAR名>' <代码目录> <脚本目录> <配置文件>`，被引用就留。
- 🚨 **静音单个刷屏源要写 rsyslog 过滤规则，验证必须双向。** 内核参数关不掉硬件错误上报
  （AER 是硬件层上报，`pcie_aspm` / `pcie_port_pm` 只能减少触发），**只能在日志层静音**。
  规则写成独立文件（如 `49-aer-suppress.conf`），**编号必须小于默认规则文件**（`50-default.conf`），
  否则规则先被吃掉、配置看着对但完全不生效。语法只用 legacy 的 `:msg, contains, "<串>"   ~`，
  **不要自造属性名**（自造会报 `invalid property 'xxx'`）；特征串要精确到设备号/唯一前缀，别用宽泛关键词。
  ```bash
  sudo rsyslogd -N1            # 语法校验，有 error 就中止，不要带着坏配置重启
  sudo systemctl restart rsyslog
  # 双向验证：目标文件行数零增长 + 另一日志文件仍在增长
  ```
  ⚠️ **只看「目标日志没长」不能证明生效**——rsyslog 整体挂了也会零增长，误判成「过滤有效」。
  必须同时确认另一日志文件（如 syslog）仍在正常写入。判定期间要用**行数差**（`wc -l` 取前后差），
  短窗口零新增可能是刷屏恰好停了，要跨两次观察再下结论。
- 🚨 **机器重启/关机类命令是 agent 侧绝对黑名单。** `systemctl reboot` / `poweroff` / `shutdown`
  被硬拦截，**无法通过 --yolo / approvals.mode=off / cron approve 绕过**。即使用户明确要求重启，
  只能把命令给用户、让他自己在终端跑，然后等恢复后继续验证。**不要花时间试绕法。**
  重启前先确认自启会拉起来：三个服务都 `systemctl --user is-enabled` + **`loginctl show-user <user> -p Linger`（必须是 yes，
  否则 user service 不随开机启动）** + `Restart=always`。 报出任何崩溃/异常计数之前，
  MUST 用当前状态二次确认：`journalctl --since '<本次会话开始>' | grep -ci '<unit>'`（0 次 = 历史故障）、
  `systemctl list-unit-files | grep '<unit>'`（单元已不存在 = 早被移除）。
  直接照抄旧日志的计数，会让用户去修一个早就没了的问题——纯浪费信任。
  包管理器知道哪些是缓存、哪些是已装内容；`rm -rf` 是赌它不越界。
  **已装的包在 venv 的 `site-packages` 里，与缓存目录无关** —— 删缓存不影响任何已装的东西，
  唯一代价是下次装包重下。这条要在回答「X 是啥 / 有必要留么」时先给结论（见 `agent-communication-discipline` 5.30）。
- 🚨 **「定期清垃圾箱」的任务要区分「提醒型」与「执行型」——名字里带「提醒」的只打印命令。**
  实测一个双周任务把 `trash-empty` 的命令串**打印在报告末尾**让用户手跑，却被我描述成
  「30 天后自动清空」；用户据此答「不清，等时间到自动清」——而那个任务只提醒、不执行。
  **规则：给用户说「到时间会自动做 X」之前，先确认那个 job 真的执行**（读脚本，不看名字）。
  **工具支持某参数 ≠ 有任务在调它。**
  执行型的正确形态是调用时**只清超过保留期的**（`trash-empty --days 30 --force`，
  默认干跑、加 `--force` 才真删），做法照抄 freedesktop.org Trash 规范的官方 FAQ（`@daily trash-empty 30`）——
  不用装任何第三方工具。另外可配 `gtrash prune --size 5GB` 式的**体积上限**，但那是可选的：
  同一分区 + 固定保留期已经够用，再加一层是过度设计。
- 🚨 **验证 trash 的删除逻辑，不要在真实 `~/.trash` 上注入假数据。**
  做法是在 `log.csv` 补一条 N 天前的条目，然后跑脚本——而脚本**会真的把它删掉**，
  于是在用户真实垃圾箱里做删除测试。正确做法分两层：① 纯逻辑层用内联样本验解析/分支
  （如「输出含 `已删除 0 项`」必须报「未清理」而非「清理完成」）；② 真实环境只做**只读实跑**
  （此时全是保留期内条目，正确结果应是「未清理」且 trash 条数不变）。
  同一条也适用于**守护进程拦下来的操作**：被拦说明风险判断是对的，不要换措辞重试。
- 🚨 **清单里的图片可能是「内容系列」不是「独立项目」**：同一话题连着多张同系列图（编号 02/08~06/08）时，
  整批同质，**读一张就能判定归属**，逐张实读是白花时间。
- **嵌套目录 bug**：`cd` 后 `mkdir Camera/YYYY-MM` 会造出 `Camera/Camera/YYYY-MM`。**永远用绝对目标路径 + `mkdir -p`**。
- **敏感数据隔离**：绝不把家庭/健康档案悄悄并进通用树；保持分离并告知用户。
- 🚨 **自建脚本目录不在 git 里时，每次改动都不可回滚 —— 顺手建仓。** 技能库有版本控制时，**最有价值的修复**常常正好落在**没被版本控制覆盖**的目录（用户脚本、插件、看门狗），
  而那些目录只靠一个 `.bak-<日期>` 单点兜底。下一次误操作就找不回来了。
  **判据：本次任务改了文件但它的目录没有 git ⇒ 任务收尾前必须问一句「要不要建仓」**，
  并同时给出选项：(A) 纳入 git（**先脱敏**：API key / chat_id / 凭据再入库）、
  (B) 只清 `.bak` 堆积、(C) 都不动。**默认建议 A**，并说明理由——
  「技能库 20 个提交 vs 房产脚本 0 个提交」这种对比本身就是最有说服力的论据。
- **纳入 git 前的脱敏**：把写死的会话 id / 收件人 / 凭据换成环境变量读取
  （`os.environ.get('X', '<原值>')`），既去掉敏感值又保持原行为可跑。
  ⚠️ **`.gitignore` 至少覆盖**：`*.bak` `*.bak-*` `__pycache__/` `*.pyc` `*.db` `*.env` `*.key` `*.pem` `*.zip`。
  **入库后立刻反查一遍**：敏感值不只藏在正文里，**`git add` 路径写错时会把整个目录的无关文件带进来**——
  加完先 `git diff --cached --stat` 数一遍文件数，与预期不符就 `git reset` 重来。
  再加一条：**`git log --all --diff-filter=A --name-only | grep -E "<私料关键词>"` 必须零命中**——
  「现在文件不在库里」不等于「从没进过库」。若 git 历史里搜到同名词的命中，先确认是它物再下结论（实测那两处是别人聊天记录里的同名词，不是自己的私料）。
- 🚨 **写复盘/文档时引用的示例串会让 pre-commit 的凭据扫描误报，提交被拦。**
  复盘里常要举「什么样的写法会泄露凭据」的例子，而那些例子本身就是 `API_KEY_123` / 一串十六进制
  这类形状，**凭据扫描 hook 读不出上下文，只认形状**。
  **处置顺序（别一被拦就去改写规则里的例子，那是在删真实信息）**：
  ① `git add` 后 `git diff --cached --stat` 核对文件清单、无敏感文件；
  ② 确认示例确实是举例而非真值：`git diff --cached | grep -nE '<你的私料关键词>'` 要零命中；
  ③ 三项都过才 `git commit --no-verify`，**并在汇报里写明「用了 --no-verify，因为什么」**。
  **⛔ `--no-verify` 不是绕过闸门的常规手段**：它绕过的是本次提交的全部 hook，
  代价是本次也跳过了格式、测试、其它扫描。**用它的前提是你已经手工跑过那些 hook 各自要做的事。**
- **中文文件名 + shell 引号**：带空格/引号/`'` 的路径会炸掉内联 glob。用 Python（`os.walk`）或 `find -print0 | xargs -0` 枚举；
  含撇号路径（`Kent'AI`、`王浩纪念照片`）一律走 `from hermes_tools import terminal` + `os.walk` Python 块，
  **只在没有这些字符时用 `terminal`**；另外 `workdir=/` 可以绕开 `cd H:\Hermes` 的幽灵报错。

## References

- `references/original-safe-file-organization-en.md` — **本技能合并前原英文正文（逐字留档）**
- `references/workflow-and-examples.md` — 原 `archive-hygiene` 的 examples（逐字）：3046 拓扑、VAULT 解剖、敏感边界
- `references/archive-hygiene-two-zones.md` — 原 `archive-hygiene` 正文（逐字）：两区原则、工作流、硬规则、Obsidian 解剖
- `references/safe-rm-trash-design.md` — 原 `safe-delete-trash` 正文（逐字）：trash 三工具设计与全部规则
- `references/script-audit-rules.md` — 原 `script-audit-cleanup` 正文（逐字）：排除范围、流程、陷阱、常见 bug
- `references/techniques.md` — 精确命令模式（清点/chown/日期解析/MD5/terminal 幽灵修复）
- `references/photo-library-structure.md` / `references/photo_library.md` — 照片库年/事件树 + `.meta.json` 云标记规范；EXIF 年归档脚本
- `references/knowledge-base-extraction.md` — 从程序目录中分离知识库资产
- `references/knowledge_base_smb.md` — VAULT 提取 + SMB `[Knowledge]` 共享设置
- `references/standing-pipeline.md` — 用户定义的固定流水线 + 季度复盘 cron
- `references/remote-cleanup-workflow.md` — 远程机器清理标准流程
- `references/pitfalls-additions.md` — 追加坑清单
- `references/workflow-abc.md` — A/B/C 分批清理工作流（从主文件 §2 拆出）
- `references/3046-environment.md` — 3046/笔记本/台式机环境事实
- `scripts/dedup_find.py` — 两阶段去重（size 初筛 + SHA256 确认 + JSON 报告）
- `scripts/dedup_report.sh` — md5 重复报告器（只读、处理中文路径、并行）
- `scripts/find_dupes.sh` — MD5 重复报告模板（永不删）
- `scripts/organize_by_date.sh` — 文件名日期分类模板

## 合并说明

2026-09-27 「文件整理簇」4→1：本技能（保留原名，`file-management/safe-file-organization`）并入
`productivity/archive-hygiene`、`software-development/script-audit-cleanup`、`devops/safe-delete-trash`。
三个源的 SKILL.md 正文**逐字**落在对应 `references/*.md`；`archive-hygiene` 的 `scripts/dedup_report.sh`
搬入 `scripts/`。源目录归档于 `.archive/<name>/`，原件逐字保留；备份 `~/.hermes/skill-backups/merge-cleanup-20260927-001231/`。

**保留判断**：`archive-hygiene` 与本技能有两区原则、去重流程、保护名单等多处措辞不同的重叠叙述——
按 2026-09-27 的教训（"措辞不同 ≠ 同义"），**没有做二选一，全部逐字保留在 ref**，主文件只做整合导航。

**未并入的判断**：`safe-delete-trash`（删除机制本身）与 `script-audit-cleanup`（Windows 侧脚本审计）
主题与"整理文件"并不同源，是**同一条"安全清理"脊柱上的两个面**，因此并入本技能成为 §4 / §5，
而不是让它们各自独立成技能。
