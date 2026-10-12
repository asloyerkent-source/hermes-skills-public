# root-cause-consolidation-pass — 原 skill-library-curation/SKILL.md 第 27–94 行（逐字）

> 2026-09-26 「技能管理簇」5→1 合并：本节从主 SKILL.md 拆出，内容逐字未改。

## 先判归属：这条技能根本不属于你（external_dirs / pinned）

**「X 系列看着重叠，删了吧」——动手前先查这批技能的**真身路径**。**
索引里那一行只是**路由信号**，不是所有权：同名的 `<前缀>-*` 可能一个在主库、一整批在插件自带目录里。

```bash
grep -A5 '^skills:' ~/.hermes/config.yaml    # external_dirs 就是非主库真身
find ~/.hermes/skills ~/.hermes/plugins ~/.agents/skills -maxdepth 3 -iname '<前缀>*'
python3 -c "import json;d=json.load(open('$HOME/.hermes/skills/.usage.json'));print([(k,v.get('use_count'),v.get('state'),v.get('pinned')) for k,v in d.items() if '<前缀>' in k])"
```

| 真身在哪 | 是什么 | 唯一合法处置 |
|---|---|---|
| `skills.external_dirs`（插件自带 `<plugin>/skills/`） | **外部所有**，随插件升级被覆盖 | **改 config.yaml 摘掉那一行目录**（可逆、零删文件）；删文件 = 下次插件更新复活 |
| `pinned=true` | 用户显式保留声明 | 连内容更新都不该动；解 pin 只能由用户在前台做 |
| 主库 + 无 pin | 你自己的 | 才进合并/归档流程 |

**判据：一条技能不可删，等于这条改造的收益要按「可删的那几条」重算。**
实测一批「6 条同类」里 5 条在插件自带目录、1 条 pinned，真正可动的只剩 1–2 条——
「删 6 个技能」的提案量级因此塌掉，**必须重新报价而不是照原计划执行**。

## 算收益上限：索引里的技能到底值多少 token

合并/删除是以**小时**计的操作，先量收益量级：

```bash
python3 - <<'EOF'
import glob,re
tot=n=0
for f in glob.glob('$HOME/.hermes/skills/**/SKILL.md',recursive=True):
    t=open(f).read(); m=re.match(r'^---\n(.*?)\n---',t,re.S)
    if m:
        d=re.search(r'^description:\s*(.+)$',m.group(1),re.M)
        if d: tot+=len(d.group(1)); n+=1
print(n,tot,tot//n if n else 0)
EOF
```

注入索引的只有 `name` + `description`，实测均 **~45 字符/条** ⇒ 省下的是 **N × 60 字符**；
N=7 时约 **2.5K token / 0.2% 上下文**。
**判据：省下的在一万 token 以下、成本以小时计 ⇒ 不做，直接返回「现状已是最优解」并把数字摆出来。**

**别按前缀批量删：同族里可能有「另一条故障模式」而非同一职责的技能。**
实测排障类条目（网络隔离时的反向隧道）`use_count` 显著高于它所属的整个系列——
说明它被当独立排障入口在用，与「主功能启停」无关，按前缀删会连带删掉仍在用的那一类。

## 「用户说某功能最近没在用」——先追真实通路，再谈删

用户口中的功能名往往**不是它实际承担的职责**。删前追一遍链路：

```bash
ps aux | grep -i <关键词> | grep -v grep    # 进程还活着吗
ss -ltnp | grep <端口>                      # 端口还占着吗
```

实测：手机上到主机的真实通路是 **tailscale IP → termux → ssh**，与被点名的那条通道无关；
那条通道只是**同一件事的另一个前端**，能力上已被完全覆盖。
**结论形态是「不用处理」而不是「合并删减」——没追通路就动手，会白做一轮合并。**

## Root cause check: is the consolidation pass even ON?

Duplicates accumulate because the mechanism that would merge them ships
**disabled**. The curator has a full umbrella-building consolidation pass; it
is off unless configured, and with it off the curator creates a new skill for
every session topic it judges worth keeping — no dedup check against what
already exists.

Run this before planning any hand-merge (30 seconds, decides whether you
hand-merge or flip a switch):

```bash
cat ~/.hermes/skills/.curator_state        # look for "consolidation off"
grep -c '"action": "create"' ~/.hermes/skills/.curator_ledger.jsonl
```

`last_run_summary` reads `... llm: skipped (consolidation off)` when disabled.
Count the `create` actions: a large share of the library having been
auto-created in a single month (observed: 38 of 127) is the signature of
create-without-dedup drift — and hand-merging that will be undone by the next
session.

**The config key lives at TOP LEVEL `curator:`, not under `auxiliary: curator:`.**
`auxiliary.curator` only selects which model the curator runs on;
`_load_config()` reads `_read_config_section("curator")`, i.e. the root key.
Recognised keys and defaults: `enabled` (true), `interval_hours` (168),
`min_idle_hours` (2), `stale_after_days` (14), `archive_after_days` (30),
`consolidate` (**false**).

Preview before enabling — dry-run reports and writes an audit REPORT.md but
performs no transitions:

```bash
hermes curator run --dry-run --consolidate
```

Review that report before persisting `consolidate: true`.

**Budget for the dry-run to produce nothing.** Over ~127 skills the pass reads
every SKILL.md through the auxiliary model. With a *free* aux model
(`auxiliary.curator`) it hit a 20-minute timeout with **zero output** — no
REPORT.md, `last_report_path` and `last_run_at` unchanged. Read a silent
timeout as "the automated pass is not viable at this scale with this model",
NOT as "nothing to merge": either hand-merge the top clusters, or point
`auxiliary.curator` at a faster model first. Never flip `consolidate: true` on
the strength of a dry-run that never finished.

`hermes curator status` prints the effective config, the managed/unmanaged
split, and the least-recently-active skills — the fastest orientation there is:

```bash
hermes curator status      # interval / stale_after_days / archive_after_days / consolidate on|off / active-stale-archived counts
hermes curator usage       # per-skill use/view/patch/activity, sorted
```

Anything listed as `unmanaged (no provenance marker)` is outside the curator's
reach — foreground-created skills are never auto-staled, so counting only the
managed set understates how much is actually in the library. Two safety nets make
the automatic pass safer than hand-merging: it rewrites cron job skill
references to follow consolidations (scheduled jobs do not break), and it
refuses to prune `use=0` skills younger than 30 days (a new skill may simply
not have had its trigger yet). Its stated bar for merging is: *would a human
maintainer write this as N separate skills, or as one skill with N labeled
subsections?*

When editing `config.yaml`, back up first and use a text patch — a
YAML-library round-trip strips every comment.
