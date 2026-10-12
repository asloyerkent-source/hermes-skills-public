#!/usr/bin/env python3
"""sanitize_for_public.py — 从私有 skills 库生成可公开的副本

只做三件事，每件都可审计：
  1) 排除不该公开的目录（备份/归档/克隆/运行态/日志流水）
  2) 替换私人信息：私网 IP、手机号、Telegram/QQ id、真实家目录
  3) 输出一份替换清单（report.json），让你知道动了什么

不删原库，只读源、写目标目录。

用法：
  python3 sanitize_for_public.py --src ~/.hermes/skills --dst /tmp/hermes-skills-public
  python3 sanitize_for_public.py --src ... --dst ... --only flows,software-development   # 只出指定类目
  python3 sanitize_for_public.py --src ... --dst ... --report-only                        # 只扫描不写
"""
import argparse
import json
import os
import re
import shutil
import sys
from collections import Counter
from pathlib import Path

# ---------------------------------------------------------------- 排除规则
EXCLUDE_DIRS = {
    ".archive", ".curator_backups", ".hub", ".git", "__pycache__",
    "raw", "mid", "essence", "logs", "drafts",   # model-logging 的数据层
}
EXCLUDE_NAMES = {".curator_ledger.jsonl", ".curator_state", ".curator_suppressed",
                 ".bundled_manifest", "INDEX.md"}
EXCLUDE_PREFIX_FILES = (".snapshot_now_",)
# 这三个是 clone 自他人仓库，有自己的 upstream，不该并进我们的公开库
NESTED_REPOS = {"hermes-hud", "china-briefing", "skill-evolution"}

TEXT_EXT = {".md", ".py", ".sh", ".json", ".yaml", ".yml", ".txt", ".cfg", ".toml", ""}

# ---------------------------------------------------------------- 替换规则
#
# 词边界一律用 (?<![A-Za-z0-9_]) / (?![A-Za-z0-9_])，**不要用 \b**：
# Python 的 \b 把中日韩字符也算 \w，所以「$HOME目录整洁」里
# s 与 目 之间没有边界，\b 不触发，这条私人路径就整条漏过去（2026-09-30 实测）。
_NB_L = r"(?<![A-Za-z0-9_])"
_NB_R = r"(?![A-Za-z0-9_])"

SUBS = [
    # Telegram / QQ id。
    # QQ id 是 32 位大写十六进制，形态唯一，**不加左边界**：
    # 泄露点常常在检测脚本自己的正则里（如 re.compile(r"\b<QQ_ID 前4位>...")），
    # 左边紧邻的 `b` 属于 \w，左边界会正确地拒绝匹配 —— 结果整条漏出去（2026-09-30 实测）。
    (re.compile(r"<QQ_ID>" + _NB_R), "<QQ_ID>"),
    (re.compile(_NB_L + r"<TELEGRAM_ID>" + _NB_R), "<TELEGRAM_ID>"),
    # 真实家目录（后跟中文也算）
    (re.compile(r"$HOME" + _NB_R), "$HOME"),
    (re.compile(r"$HOME\b"), "$HOME"),
    (re.compile(_NB_L + r"<user>@"), "<user>@"),
    # 私网地址：整段 RFC1918 全覆盖，真机段 -> example 段（保留可读性）。
    # **2026-10-12 改成「按整段」而不是「按用过的网段列」。** 原写法只列了 .2.x / .31.x
    # 两个真实用过的段，于是 192.168.99.X 原样漏进了产物（实测残留 4 处）。
    # 根因与 2026-09-30 事故同源：**按「我记得用过的值」列规则，而不是按「这一类」列**。
    # 边界用 (?<!\d)/(?!\d) 而不是词边界：IP 的天然边界是数字，
    # 词边界遇到 `x192.168.99.X` 这种紧邻字母的写法会漏。
    # 替换目标里的 X 不是数字，不会被本规则二次匹配。
    (re.compile(r"(?<!\d)192\.168\.\d{1,3}\.\d{1,3}(?!\d)"), "192.168.99.X"),
    (re.compile(r"(?<!\d)172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}(?!\d)"), "172.31.99.X"),
    (re.compile(r"(?<!\d)10\.\d{1,3}\.\d{1,3}\.\d{1,3}(?!\d)"), "10.99.99.X"),
    # **通配写法 `192.168.99.X`（2026-10-12 补）**：末位写成字面 `x`/`X` 的网段写法，
    # 上面三条 `\d{1,3}` 全都匹配不到 —— 实测产物里残留 5 种真实网段共 35 处。
    # **这个盲区两个工具都有**：preflight 的 TOPOLOGY 正则也要求末两段是数字，
    # 所以它报「TOPOLOGY 0 ✓」是**假阴性**，不是真干净。
    # 教训：换工具≠换视角 —— 两个工具出自同一个人、同一个心智模型时，
    # 会带着**同一个盲区**。独立验证要挑「判据构造方式不同」的工具，不是「文件名不同」的。
    (re.compile(r"(?<!\d)192\.168\.\d{1,3}\.[xX](?![A-Za-z0-9])"), "192.168.99.X"),
    (re.compile(r"(?<!\d)172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.[xX](?![A-Za-z0-9])"), "172.31.99.X"),
    (re.compile(r"(?<!\d)10\.\d{1,3}\.\d{1,3}\.[xX](?![A-Za-z0-9])"), "10.99.99.X"),
    # 主机名
    (re.compile(_NB_L + r"<hostname>" + _NB_R), "<hostname>"),
    (re.compile(_NB_L + r"<win-host>" + _NB_R), "<win-host>"),
    (re.compile(_NB_L + r"<win-host>" + _NB_R), "<win-host>"),
    # VAULT 之类的私人路径名
    (re.compile(r"VAULT"), "VAULT"),
    (re.compile(r"VAULT"), "VAULT"),
    # GitHub 账户名（2026-10-12 补）。**规则表原先压根没有「账户名」这一类** ——
    # 与 2026-09-30 事故同源：按「我记得有什么」列，不是按「泄露后果」列。
    # 账户名单独看不算敏感，但它 + 仓库名就是一个可被检索的身份标识，
    # 会把「这个公开库属于谁」直接钉死（公开库名当初就是为这个才不写进文档的）。
    (re.compile(r"<gh-account>"), "<gh-account>"),
    # 操作系统用户目录（2026-10-12 补，**按类不按值**）。
    # 库里有 200+ 处 `C:\Users\<user>` 与 `/Users/<user>`；
    # 实测还有人名形态（`/Users/<user>`）。逐个值加规则永远漏 ——
    # 改成「整个用户目录这一类」：任何 `<盘>:\Users\<名>` 与 `/Users/<名>` 都归一。
    # 左边界排除 `/` 与 `:` 避免误伤 URL 路径（如 `example.com/Users/x`）。
    # **分隔符两种都要覆盖**：Windows 路径既写 `C:\Users\<user>` 也写 `C:/Users/<user>`
    # （Python 里常写后者），只写反斜杠会漏掉一半 —— 2026-10-12 实测。
    # 用捕获组保留原分隔符，替换后路径形态不变。
    (re.compile(r"(?<![\w:/\\])([A-Za-z]:)([\\/])Users\2([A-Za-z0-9_.-]+)"),
     r"\1\2Users\2<user>"),
    (re.compile(r"(?<![\w:/])/Users/[A-Za-z0-9_.-]+"), "/Users/<user>"),
    # ---- 以下四类是 2026-09-30 补的，之前**完全没有**，而真料恰好就在这些文件里 ----
    # 事故经过：公开库推上去 2.5 小时后才发现里面有身份证号 + 家庭住址 + 支付宝账户。
    # 根因不是「漏替换」，是**规则表里压根没这一类** —— 我一直在写「怎么防私料外泄」的
    # 技能，自己在技能里贴了真料。
    # 教训：**脱敏规则要按「泄露后果」排，不是按「我以为有什么」排**。
    # 身份证/住址/支付账户的后果都比手机号重，却一条都没设。
    # 私钥块（2026-10-01 补·自测发现的唯一缺口）：整块脱敏，不只脱头——
    # 只脱 BEGIN 行会让 base64 正文原样泄露，比不脱更危险。
    (re.compile(r"-----BEGIN (?:[A-Z ]*)PRIVATE KEY-----"
                r"(?:(?!-----END)[\s\S])*?"
                r"-----END (?:[A-Z ]*)PRIVATE KEY-----"), "<PRIVATE_KEY_BLOCK>"),
    # 18 位身份证（含末位 X）
    (re.compile(r"(?<!\d)\d{17}[\dXx](?!\d)"), "<ID_CARD>"),
    # 银行卡 / 支付账户：支付宝、银行卡、账号后跟一串数字
    (re.compile(r"(支付宝|收款|银行卡|银行账户|账号)[：:=\s]*\d{6,20}"), r"\1<ACCOUNT>"),
    (re.compile(r"(?<!\d)\d{16,19}(?!\d)"), "<CARD_NO>"),   # 纯长数字卡号
    # 住址：xx省xx市xx区xx路xx号xx室/xx栋xx单元xx室
    (re.compile(r"[\u4e00-\u9fa5]{2,8}(省|市|区|县)"
                r"[\u4e00-\u9fa5]{2,10}"
                r"(路|街|道|巷)\d{1,5}号"
                r"[\u4e00-\u9fa5\d]{0,12}"), "<ADDRESS>"),
    # 邮箱（QQ 邮箱/163/gmail 等常见形态）
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+"), "<EMAIL>"),
]
# 手机号：中国大陆 1[3-9] 开头 11 位。放在最后（前面规则先跑完），
# 避免把已经是占位符的东西再匹配一次。
PHONE = re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)")


def is_texty(path: Path) -> bool:
    if path.suffix.lower() in TEXT_EXT:
        return True
    try:
        path.read_text(encoding="utf-8")
        return True
    except (UnicodeDecodeError, OSError):
        return False


def sensitive_literals() -> list[tuple[str, str]]:
    """本脚本源码里出现的「私人值字面量」-> 占位符。

    脱敏器脱不净自己：SUBS 里每条正则都写着真机 IP / 家目录 / 主机名 / id。
    要让脚本进公开库，得把这些字面量在副本里替换成占位符。
    做法：反向利用 SUBS 自己 —— 用每条正则去匹配本文件源码，替换成对应 repl。
    这样不新增一份要维护的字面量表，规则改了这里自动跟着改。
    """
    try:
        here = Path(__file__).read_text(encoding="utf-8")
    except OSError:
        return []
    out = []
    for pat, repl in SUBS:
        out.append((pat.pattern, repl))     # 正则原文 -> 占位符
    # 额外：单独的字面量（不出现在正则里但出现在注释/文案里）。
    # **别在这里手写手机号原文**（2026-10-12 实测：这行本身就是 preflight 抓到的一处 PII）——
    # 手机号已经有 PHONE 规则，直接从配置派生。
    for lit in ("<hostname>", "<win-host>", "<win-host>", "VAULT",
                "VAULT", "<QQ_ID>",
                "<TELEGRAM_ID>"):
        out.append((re.escape(lit), _LIT_PLACEHOLDER.get(lit, "<PRIVATE_LITERAL>")))
    out.append((PHONE.pattern, "<PHONE>"))
    return out


_LIT_PLACEHOLDER = {
    "<hostname>": "<hostname>", "<win-host>": "<win-host>",
    "<win-host>": "<win-host>", "VAULT": "VAULT", "VAULT": "VAULT",
    "<PHONE>": "<PHONE>", "<QQ_ID>": "<QQ_ID>",
    "<TELEGRAM_ID>": "<TELEGRAM_ID>",
}


def self_redact(text: str) -> str:
    """脱敏脚本自己：把源码里的私人字面量换成占位符。

    2026-09-30 实测踩过：脚本本身被当成普通文本复制进公开库，
    于是「负责脱敏的那份文件」把全部真机 IP / id / 主机名原样带出去了 ——
    复扫抓到 11 处残留，全来自它自己和它的 SKILL.md。
    """
    for pat, repl in sensitive_literals():
        try:
            text = re.sub(pat, repl, text)
        except re.error:
            continue
    return text


def sanitize_text(text: str, counts: Counter) -> str:
    """按规则表逐条替换。计数用规则名（r0/r1/…），不记正则原文——
    正则原文里含被脱敏的字面量，进报告就等于二次泄露（2026-09-30 实测）。"""
    for i, (pat, repl) in enumerate(SUBS):
        text, n = pat.subn(repl, text)
        if n:
            counts[f"r{i}"] += n
    text, n = PHONE.subn("<PHONE>", text)
    if n:
        counts["r_phone"] += n
    return text


def should_skip(rel: Path) -> bool:
    parts = rel.parts
    if any(p in EXCLUDE_DIRS for p in parts):
        return True
    if any(p in NESTED_REPOS for p in parts):
        return True
    name = rel.name
    if name in EXCLUDE_NAMES:
        return True
    if any(name.startswith(p) for p in EXCLUDE_PREFIX_FILES):
        return True
    return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--dst", required=True)
    ap.add_argument("--only", default="", help="逗号分隔的类目名，如 flows,devops")
    ap.add_argument("--report-only", action="store_true")
    args = ap.parse_args()

    src = Path(args.src).expanduser().resolve()
    dst = Path(args.dst).expanduser().resolve()
    only = {x.strip() for x in args.only.split(",") if x.strip()}

    counts = Counter()
    kept, skipped = [], []
    for p in sorted(src.rglob("*")):
        if p.is_dir() or ".git/" in str(p):
            continue
        rel = p.relative_to(src)
        if should_skip(rel):
            skipped.append(str(rel))
            continue
        if only and rel.parts[0] not in only:
            skipped.append(str(rel))
            continue
        if not is_texty(p):
            skipped.append(str(rel) + "  [binary]")
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            skipped.append(str(rel) + "  [unreadable]")
            continue
        clean = sanitize_text(text, counts)
        if rel.name == Path(__file__).name:
            # 脱敏器脱自己（见 self_redact 的 docstring）
            before = len(clean)
            clean = self_redact(clean)
            counts["r_self"] += 1
        if not args.report_only:
            out = dst / rel
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(clean, encoding="utf-8")
        kept.append(str(rel))

    # 报告本身也要脱敏：
    #  1) kept_sample/skipped_sample 带着**未脱敏的原值**（2026-09-30 实测：报告文件自身
    #     把 QQ 号、家目录、主机名又泄了一遍）；
    #  2) replacements 的 key 是**正则原文**，里面也含被脱敏的字面量
    #     （如 "subs:\\b<win-host>\\b": 16）——改用规则名，不记原文。
    #  3) **本脚本自己**（sanitize_for_public.py）也是文本文件，它的源码里写着全部
    #     正则原文 —— 即「被脱敏的字面量」全都在。要让它进公开库，就得把
    #     正则的字面量部分也参数化或占位化，否则脱敏器脱不净自己。
    #     这里选择：公开副本里把整份脚本的 SUBS 换成占位版本。
    rule_names = ["TELEGRAM_ID", "QQ_ID", "HOME_PATH", "HOME_PATH_B", "HOME_USER",
                  "PRIV_IP_192_168_2", "PRIV_IP_192_168_31", "PRIV_IP_172_16", "PRIV_IP_10",
                  "HOSTNAME", "WIN_HOST_DESKTOP", "WIN_HOST_231",
                  # 规则名本身**不能含被脱敏的字面量**（曾写成 VAULT_VAULT，
                  # 报告文件又把它原样吐出来 = 二次泄露）。改用中性名。
                  "VAULT_NAME_1", "VAULT_NAME_2", "SELF_REDACT"]
    by_rule = {n: counts.get(f"r{i}", 0) for i, n in enumerate(rule_names)}
    by_rule["PHONE"] = counts.get("r_phone", 0)
    report = {
        "generated_by": "sanitize_for_public.py",
        "src": "<source>/.hermes/skills",
        "dst": "<destination>",
        "kept_files": len(kept), "skipped_files": len(skipped),
        "replacements_total": sum(counts.values()),
        "replacements_by_rule": by_rule,
        "excluded_dirs": sorted(EXCLUDE_DIRS),
        "excluded_nested_repos": sorted(NESTED_REPOS),
        "note": "本报告刻意不含原始文件名样本与正则原文，避免把待脱敏的值原样带出来。",
    }
    rp = dst / "SANITIZE-REPORT.json" if not args.report_only else Path("/tmp/sanitize-report.json")
    rp.parent.mkdir(parents=True, exist_ok=True)
    rp.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"保留 {len(kept)} 个文件，跳过 {len(skipped)} 个")
    print(f"替换统计：{json.dumps(dict(counts), ensure_ascii=False, indent=2)}")
    print(f"报告：{rp}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
