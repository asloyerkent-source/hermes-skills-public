---
name: skill-publish
description: Use when 把自用技能库发布到 GitHub，或更新已发布的公开版。含脱敏规则与推送流程。
---

# 技能库发布（私有 + 公开双库）

## 两个库的分工

| 库 | 可见性 | 内容 |
|---|---|---|
| `<gh-account>-source/hermes-skills` | 私有 | 全量，含日志流水（被 gitignore） |
| 公开库 | 公开 | 脱敏后 79 个技能 + README |

私有库是**版本记录**（"改之前长什么样"），公开库是**对外输出**。两者独立演进，不要互相对齐。

> 公开库名故意不写具体名字：文档本身会被同步/提交，而仓库 URL 加上你的账户名
> 就是一个可被检索的标识（2026-09-30 事故后改）。

## 常规更新流程

```bash
# 1. 私有库：先记录变更
cd ~/.hermes/skills && git add -A && git commit -m "..." && git push

# 2. 重新生成公开版
rm -rf /tmp/hsp
python3 ~/.hermes/skills/devops/skill-publish/scripts/sanitize_for_public.py \
    --src ~/.hermes/skills --dst /tmp/hsp

# 3. 推前必扫：复扫模式从本机配置生成，别把真值硬写在这份文档里
#    （这份 SKILL.md 自己就因硬写真值而泄漏过 —— 见下方「坑」第 5 条）
python3 -c "
import re, subprocess, sys
sys.path.insert(0, 'scripts')
import sanitize_for_public as S
pats = [p.pattern for p, _ in S.SUBS] + [re.escape(x) for x in S._LIT_PLACEHOLDER]
bad = 0
for pt in pats:
    r = subprocess.run(['grep','-rEoh',pt,'.'], capture_output=True, text=True).stdout
    n = len([x for x in r.split() if not x.startswith('./.git/')])
    if n:
        print('  残留', pt[:40], '=', n); bad += n
print('  残留合计:', bad)"

# 3.5 独立体检：换一个工具扫【产物】。
#     上面第 3 步用的是脱敏器自己的规则表 —— 那等于生产者审自己：
#     规则表里没设的类，复扫也照样 0 残留，给出假的安心。
#     换 publish_preflight.py（另一套独立模式）扫 /tmp/hsp，才是真验收。
python3 ~/.hermes/skills/knowledge-management/skill-library-curation/scripts/publish_preflight.py \
    --root /tmp/hsp
# 它只扫源码目录、不看产物时，等于没验 —— 必须指向产物。

# 4. 密钥门禁：真密钥交给现成工具，不自己判
gitleaks detect --no-git --source /tmp/hsp --report-format json \
    --report-path /tmp/gl.json --exit-code 0
# **gitleaks 命中不等于有真密钥**（实测 38 条里 37 条是误报：sha256 文件名、
# GitHub 用户名、测试里的 ***）。但真密钥确实靠它才能找到 ——
# 2026-09-30 我的自研扫描漏了 QQ App Secret（判成「含 x 所以是占位符」），
# gitleaks 一次就抓到了。**每条命中都要人工看，不能只数条数。**

# 5. 提交推送
cd /tmp/hsp && git add -A && git commit -m "..." && git push
```

## 2026-09-30 事故：推了 2 小时 48 分才发现身份证号在里面

公开库推上去后近 3 小时，删库前才发现里面有用户**身份证号** + **家庭住址** + **支付宝账户**，
散在 6 个文件里（其中一个是「教别人怎么脱敏」的那份文档）。库已删、已转私有、确认未被爬虫索引。

**根因不是「漏替换」，是规则表里压根没有这一类。** 第一版 SUBS 只有手机号/私网IP/家目录/主机名，
因为那是我**当时想得到的**。按泄露后果排，身份证、住址、支付账户都比手机号重，却一条没设。

**教训：脱敏规则要按「泄露后果有多重」列，不是按「我记忆里有什么」列。**
写规则时对每个值问一句：**这东西泄露出去，最坏后果是什么？** 后果越重的越要先设。

## 私有库也要脱敏：`sanitize_mirror.py`

私有库 ≠ 可以放真值。GitHub 上的私有库一旦转公开、被协作者拉取、或账户被盗，
真值就出去了；而且**历史里的真值删不掉**（改 HEAD 不影响旧提交）。

**核心约束**：`~/.hermes/skills` 既是活技能库（技能必须保留真路径才能在本机跑）
又是版本库。所以**不能就地改历史** —— 建镜像库，在镜像里逐提交脱敏，再 force-push。

```bash
# 1. 备份（必做，force-push 不可逆）
git bundle create ~/.hermes/backups/skills-all-$(date +%Y%m%d-%H%M).bundle --all
#    备份要验证能恢复：git clone <bundle> /tmp/t && cd /tmp/t && git log --oneline | wc -l

# 2. 生成脱敏镜像（逐提交过滤）
python3 scripts/sanitize_mirror.py --src ~/.hermes/skills --dst /tmp/skills-mirror

# 3. 三重验证（缺一不可，见下）
python3 scripts/test_sanitize_rules.py                       # 规则表自测
python3 scripts/audit_mirror_skills.py --root /tmp/skills-mirror --only-dirty   # 逐技能
python3 scripts/verify_mirror_clean.py --repo /tmp/skills-mirror                # 全历史对象

# 4. 推送
cd /tmp/skills-mirror && git remote add origin <私有库URL> && git push -f origin HEAD:master
```

### 为什么必须三重验证（各自能抓到对方漏的）

| 工具 | 查什么 | 抓不到的 |
|---|---|---|
| `test_sanitize_rules.py` | 规则本身对不对（正/负/变体） | 规则没覆盖的类 |
| `audit_mirror_skills.py` | **按技能分组**，逐个体检 | 历史里的旧提交 |
| `verify_mirror_clean.py` | **每个历史 blob**（含悬挂对象） | 规则没覆盖的类 |

**`git log -S <真值>` 不足以断言历史干净** —— 它只找「字符串数量变化」的提交，
即增删点。要断言「挖不出来」必须把每个 blob 的每个字节过一遍。

### 镜像脱敏踩过的坑（每条都实测过）

- **读不了 ≠ 干净**。`read_text(encoding="utf-8")` 遇到非法 UTF-8 字节会抛异常，
  `except: continue` 就等于**整个文件静默跳过脱敏**。实测一个含坏字节的
  `INDEX.md.bak-*` 把真机 IP 原样带进了历史。**用 `errors="surrogateescape"` 读写**。
- **`is_symlink()` 必须放在 `is_file()` 之前**。软链指向目录时 `is_file()` 返回 False，
  指向库外时直接断链 —— 放后面就永远到不了（实测加了 symlink 分支但位置不对，6 个软链一个没清掉）。
  库里指向 `~/.agents/skills/` 的软链是**别人的技能**，该剔除而不是解引用。
- **`.bak` 文件要在过滤阶段就删**，不能只靠 `.gitignore` —— 历史里已经进来的挡不住。
- **`filter-branch --tree-filter` 的 helper 必须放仓库外**。它在 `.git-rewrite/t`
  临时检出目录里跑，放仓库根目录会找不到。
- **Windows 路径两种分隔符都要覆盖**：`C:\Users\<user>` 和 `C:/Users/<user>`（Python 里常写后者），
  只写反斜杠漏一半。
- **检查器要豁免自己产出的占位符**，也要豁免**教学示例**（`/home/xxx`、`C:\Users\<user>`）。
  实测审核器把 13 个技能里一半报成残留，全是「教别人怎么脱敏」的示例文本 ——
  报告全是假阳性就没人看了。
- **`cat-file --batch` 的输出要先剥头再扫**。SHA-1 十六进制串里含 16-19 位连续数字，
  会被「卡号」规则命中（实测 2 处假阳性）。检查器扫到自己的输出格式 = 又一次「守卫自己不做守卫」。

## 脱敏踩过的坑（每条都实测过）

- **脱敏器自扫不算独立验证**。第 3 步的复扫和脱敏器共用同一张 SUBS 表 —— 规则里没有的类，
  复扫必然报 0，制造假的安心。独立验证必须是**换一个工具**（`publish_preflight.py`，
  另一套模式：凭据/手机号与平台 ID/私网 IP/家目录），且扫的是**产物**不是源目录。
  实测 2026-10-12：源目录扫出 762 处 PII + 277 处内网 IP；脱敏产物再扫仍剩 15 处 PII + 4 处内网 IP，
  其中内网 IP 全部来自规则表覆盖外的网段（表里当时只有两个「用过的」段）。
- **换工具 ≠ 换视角**。`publish_preflight.py` 的 TOPOLOGY 正则和脱敏器的 IP 规则**要求末两段都是数字**，
  于是末位写成字面 `x` 的网段写法（`192.168.99.X`）**两个工具都看不见** —— 我一度以为
  「换工具扫出 0 就是干净了」，其实那是我自己写的另一个工具带着**同一个盲区**，
  报的是假阴性。实测产物里这类写法残留 5 种真实网段共 35 处。
  **独立验证要挑「判据构造方式不同」的工具**（如 gitleaks 用熵+形态，不看白名单），
  不是「文件名不同」的工具。两个工具出自同一个人的同一个心智模型时，盲区会一模一样。
- **规则要按「类」列，不是按「我记得用过的值」列**。这是 09-30 事故的同一个根因，
  10-12 又以另一种形态复发：内网 IP 只列了当时用过的两个段，于是没用过的那个段原样漏进产物。
  改法：`192.168.x.x` 整段覆盖 + `172.16–172.31` 整段 + `10.x`，**再加上通配写法 `192.168.99.X`**，
  而不是逐台机器加一条。同理，「账户名」这一类原先压根没有 —— 账户名 + 仓库名是可被检索的身份标识。
- **IP 的边界是数字，不是词字符**。用 `(?<!\d)` / `(?!\d)`，不要用 `(?<![A-Za-z0-9_])`：
  后者遇到 `x192.168.99.X` 这种紧邻字母的写法会漏。**同一条规则表里两种边界混用是 bug 温床。**
- **规则表改了要跑 `scripts/test_sanitize_rules.py`**（12 组样本，负样本最关键：
  已脱敏的占位符不能被二次匹配、公网 IP 与 `172.15`/`172.32` 不能误伤）。
  这个测试是**必须留的**：我在同一轮里改了 3 次规则，每次都可能引入新的误伤，
  靠人眼看 diff 看不出「新规则会不会把 `v1.2.3.4` 也吃掉」。
- **检查器要先把「自己的占位符」剔掉再匹配**。给 TOPOLOGY 加了通配写法支持后，产物立刻报出
  267 处「内网地址」—— 全是脱敏器写进去的 `192.168.99.X`。占位符和真值形态相同，
  检查器必须显式排除自己产出的占位形态（`PLACEHOLDER_IPS.sub(" ", line)` 后再匹配），
  否则**修好假阴性就换来一堆假阳性**。注意别用「整行含占位符就跳过」——那会让
  「占位符 + 真 IP 同行」的整行漏检。
- **守卫自己不做守卫**。写「防私料外泄」的技能，自己的 SKILL.md 里却写着用户真实住址片段
  当敏感词示例。**先拿扫别人的工具扫自己**。见 `private-data-egress-guard` 的 2026-09-30 事故段。
- **现成工具能补你没想到的那类**。真密钥用 gitleaks（不要自己写正则判）——
  我自研的扫描漏了真密钥，gitleaks 抓到。但**它的命中要逐条看**（误报率极高）。
- **不能用 `\b` 做词边界**。Python 把中日韩字符也算 `\w`，所以「家目录+中文」这种写法
  `\b` 不触发，私人路径整条漏过去。改用 `(?<![A-Za-z0-9_])` / `(?![A-Za-z0-9_])`。
- **形态唯一的长标识不要加左边界**。QQ id 是 32 位大写十六进制；泄露点常常在**检测脚本
  自己的正则里**（`re.compile(r"\b<id>")`），左边紧邻的 `b` 属于 `\w`，左边界会正确地
  拒绝匹配 —— 结果整条漏出去。
- **私网 IP 要覆盖网段写法**（`x.x.0.0/16` 那种）和全 255 段，别只写 `\.d+`。
- **脱敏器脱不净自己**。`sanitize_for_public.py` 是普通文本文件，它的源码里写着**全部
  私人字面量**（真机 IP / id / 主机名全在正则里）—— 负责脱敏的那份文件自己全泄了。
  2026-09-30 实测：复扫抓到 11 处残留，全部来自它和它的 SKILL.md。
  修法：写副本时对自身再套一层 `self_redact()`（反向利用 SUBS 去匹配自己的源码）。
- **文档里的「扫描清单」和「替换示例」本身也是泄露点**。写
  把 IP 段、手机号逐个列进 `for p in ...` 这种清单，等于把要脱敏的东西又抄了一遍。
  清单要从配置**生成**（`import sanitize_for_public as S`），别硬写。
- **报告文件自己也会泄露**。① 统计字典的 key 是**正则原文**，里面含被脱敏的字面量；
  ② 文件名样本带原值。规则名必须用中性名（如 `VAULT_NAME_1`，别写成含私有名的那种）。
- **README 也会泄露**。写「家目录 `/home/xxx` → `$HOME`」时表格里那个例子本身就是原文。
- **扫描要含新增文件**（README/.gitignore 自己也会带私货），别只扫技能目录。
- **`.gitignore` 写完要 `git ls-files` 验**。2026-09-30 写完 gitignore 才 `git add -A`，
  但两个文件当时还没被规则覆盖，进了基线 commit —— **gitignore 只能挡未来，挡不了已入库的**。
  入库前跑 `git ls-files | grep <要排除的目录>` 确认 0。
