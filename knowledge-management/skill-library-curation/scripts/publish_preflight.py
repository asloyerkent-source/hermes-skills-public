#!/usr/bin/env python3
"""publish_preflight.py — 技能库开源前的泄露体检（只读，不修改任何文件）

回答「我这些技能能上传 GitHub 吗」时先跑这个。

用法:
  python3 publish_preflight.py --root ~/.hermes/skills
  python3 publish_preflight.py --root ~/.hermes/skills --json

输出分类:
  CRED_HIGH  真实 API key / token / 私钥（已过滤测试占位）
  PII        手机号、平台 ID（QQ / Telegram）
  TOPOLOGY   私网 IP
  ARCHIVE    不该上传的备份/归档目录
  VCS        已带 .git 且 remote 指向他人的子目录
"""
import argparse
import json
import os
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

# 不该上传的目录名
ARCHIVE_DIRS = {".archive", ".curator_backups", ".git", "__pycache__", "node_modules", ".venv"}
SCAN_SUFFIX = {".md", ".py", ".sh", ".json", ".yaml", ".yml", ".toml", ".txt", ".cfg", ".ini"}

# 真实凭据特征（长度阈值已按各家实际格式收紧）
CRED_PATTERNS = [
    ("openai/sk", re.compile(r"\bsk-[A-Za-z0-9_\-]{32,}\b")),
    ("github-pat", re.compile(r"\bghp_[A-Za-z0-9]{30,}\b")),
    ("github-oauth", re.compile(r"\bgho_[A-Za-z0-9]{30,}\b")),
    ("aws-akid", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("slack", re.compile(r"\bxox[baprs]-[A-Za-z0-9\-]{20,}\b")),
    ("telegram-bot", re.compile(r"\b\d{9,10}:[A-Za-z0-9_-]{30,}\b")),
    ("private-key", re.compile(r"BEGIN (?:RSA |OPENSSH |EC |PGP )?PRIVATE KEY")),
]
# 测试占位：含 ... / abc / < > 之类，一律不算真凭据
PLACEHOLDER = re.compile(r"(\.\.\.|…|xxx|XXX|<[^>]{0,20}>|abc|1234|0000|placeholder|example|EXAMPLE|dummy|redact|\*\*|sk-live\b.*\.\.\.)")

# 我们自己的占位符形态（脱敏器的替换目标）。扫描前先从行里剔除，
# 否则 `192.168.99.X` 会被下面的 TOPOLOGY 当成通配写法命中 —— 2026-10-12 实测
# 加了通配写法支持后，产物立刻报出 267 处假阳性，全是占位符。
# 用「先剔除再匹配」而不是「整行含占位符就跳过」：后者会让
# 「占位符 + 真 IP 同行」的整行漏检（is_placeholder 是整行判据，本来就偏粗）。
PLACEHOLDER_IPS = re.compile(r"(?:192\.168\.99\.X|172\.31\.99\.X|10\.99\.99\.X)")

PII_PATTERNS = [
    ("cn-mobile", re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)")),
    ("qq-id", re.compile(r"\b<QQ_ID>\b")),
    ("telegram-chat", re.compile(r"(?<![\d.])\d{9,11}(?![\d.])")),
]
TOPOLOGY = re.compile(r"\b(?:192\.168|10\.\d{1,3}|172\.(?:1[6-9]|2\d|3[01]))\.\d{1,3}\.\d{1,3}\b"
                      # 末位写成字面 x/X 的通配写法（`192.168.99.X`）—— 2026-10-12 实测
                      # 原正则要求末两段都是数字，这类写法**整个漏掉**，而脱敏器的规则表
                      # 当时也漏（同一个盲区），于是两个工具一起报「0 ✓」，是假阴性。
                      # 修一边不够：**检查器和被检查对象共享同一个心智模型时，必须两边都修。**
                      r"|\b(?:192\.168|10\.\d{1,3}|172\.(?:1[6-9]|2\d|3[01]))\.\d{1,3}\.[xX]\b")
HOME_PATH = re.compile(r"/home/[a-z0-9_-]+/")


def is_placeholder(line: str) -> bool:
    return bool(PLACEHOLDER.search(line))


def scan_text(text: str, path: str, out: dict):
    for lineno, line in enumerate(text.splitlines(), 1):
        # 拓扑判定用「剔除占位符后」的行，其余判定用原行
        topo_line = PLACEHOLDER_IPS.sub(" ", line)
        for kind, pat in CRED_PATTERNS:
            m = pat.search(line)
            if m and not is_placeholder(line):
                s = m.group(0)
                out["CRED_HIGH"].append({
                    "file": path, "line": lineno, "kind": kind,
                    "masked": s[:6] + "*" * (len(s) - 10) + s[-4:] if len(s) > 12 else s[:4] + "****",
                })
        for kind, pat in PII_PATTERNS:
            for m in pat.finditer(line):
                if is_placeholder(line):
                    continue
                s = m.group(0)
                out["PII"].append({
                    "file": path, "line": lineno, "kind": kind,
                    "masked": s[:3] + "*" * (len(s) - 5) + s[-2:] if len(s) > 7 else "****",
                })
                break
        if TOPOLOGY.search(topo_line) and not is_placeholder(topo_line):
            ips = sorted(set(TOPOLOGY.findall(topo_line)))
            out["TOPOLOGY"].append({"file": path, "line": lineno, "ips": ips})
        if HOME_PATH.search(line) and not is_placeholder(line):
            out["HOME_PATH"].append({"file": path, "line": lineno})


def dir_stats(p: Path):
    total = 0
    files = 0
    for r, d, f in os.walk(p):
        d[:] = [x for x in d if x not in ARCHIVE_DIRS]
        for x in f:
            try:
                total += (Path(r) / x).stat().st_size
            except OSError:
                # 断链软链（镜像里指向本机不存在目标的软链）：跳过，
                # 别让一个坏软链把整个体检打挂 —— 2026-10-12 实测。
                continue
            files += 1
    return total, files


def vcs_remotes(root: Path):
    out = []
    for r, d, f in os.walk(root):
        if ".git" in d:
            g = Path(r)
            try:
                res = subprocess.run(["git", "-C", str(g), "remote", "-v"],
                                     capture_output=True, text=True, timeout=10)
                remotes = [ln.split()[-1] for ln in res.stdout.splitlines() if ln.strip()]
            except Exception:
                remotes = []
            out.append({"path": str(g.relative_to(root)), "remotes": remotes})
            d.remove(".git")
        d[:] = [x for x in d if x not in ARCHIVE_DIRS or x == ".archive"]
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="技能库开源前泄露体检（只读）")
    ap.add_argument("--root", default=os.path.expanduser("~/.hermes/skills"))
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--max-report", type=int, default=8, help="每类最多列几个文件")
    args = ap.parse_args(argv)

    root = Path(args.root).expanduser()
    if not root.is_dir():
        print(f"目录不存在: {root}")
        return 2

    findings = defaultdict(list)
    archive = []
    scanned = 0

    for r, d, f in os.walk(root):
        rp = Path(r)
        parts = set(rp.relative_to(root).parts)
        if parts & ARCHIVE_DIRS:
            continue
        for x in f:
            p = rp / x
            if p.suffix not in SCAN_SUFFIX:
                continue
            try:
                text = p.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            scanned += 1
            scan_text(text, str(p.relative_to(root)), findings)

    # 2026-10-02 修 SyntaxError：原来写成
    #   (root / name, *[q / name for q in root.iterdir()] if root.is_dir() else [])
    # 三元表达式嵌在元组字面量里，Python 语法不允许（整个脚本 import 即崩）。
    # 注意 subdirs 必须在循环内算 —— 它用了循环变量 name。
    for name in sorted(ARCHIVE_DIRS):
        subdirs = [q / name for q in root.iterdir() if q.is_dir()] if root.is_dir() else []
        for cand in [root / name, *subdirs]:
            if cand.is_dir() and cand.exists():
                size, files = dir_stats(cand)
                archive.append({"path": str(cand.relative_to(root)), "bytes": size, "files": files})
                break
    remotes = vcs_remotes(root)

    total_bytes, total_files = dir_stats(root)
    uploadable_bytes = total_bytes - sum(a["bytes"] for a in archive)

    if args.json:
        print(json.dumps({
            "root": str(root), "files_scanned": scanned,
            "archive": archive, "vcs": remotes,
            "total_bytes": total_bytes, "uploadable_bytes": uploadable_bytes,
            "findings": {k: v for k, v in findings.items()},
        }, ensure_ascii=False, indent=1))
        return 0

    print(f"[preflight] root={root}")
    print(f"[preflight] 扫了 {scanned} 个文本文件（{', '.join(sorted(SCAN_SUFFIX))}）")
    print(f"[preflight] 总体积 {total_bytes/1e6:.1f}MB，排除归档后 {uploadable_bytes/1e6:.1f}MB\n")

    if archive:
        print("【ARCHIVE 必须排除】")
        for a in archive:
            print(f"  {a['path']:<24} {a['bytes']/1e6:6.1f}MB  {a['files']} 文件")
        print()

    for key, label in [("CRED_HIGH", "真实凭据（必须处理）"),
                       ("PII", "个人信息"),
                       ("TOPOLOGY", "内网地址（家庭网络拓扑）"),
                       ("HOME_PATH", "家目录路径")]:
        items = findings.get(key, [])
        files = sorted({i["file"] for i in items})
        if not files:
            print(f"【{key}】{label}: 0 ✓")
            continue
        print(f"【{key}】{label}: {len(items)} 处 / {len(files)} 文件")
        for fp in files[: args.max_report]:
            ex = next(i for i in items if i["file"] == fp)
            detail = ex.get("masked") or ex.get("ips") or ""
            print(f"    {fp}:{ex['line']}  {detail}")
        if len(files) > args.max_report:
            print(f"    …另有 {len(files) - args.max_report} 个文件")
        print()

    if remotes:
        print("【VCS】子目录已带 .git（推上去会冒充原创）")
        for v in remotes:
            print(f"  {v['path']:<40} {', '.join(v['remotes']) or '(无 remote)'}")
        print()

    cred = len(findings.get("CRED_HIGH", []))
    if cred:
        print("结论：有真实凭据，禁止上传，先处理。")
    elif findings.get("PII") or findings.get("TOPOLOGY"):
        print("结论：无凭据泄露，但含个人信息与内网拓扑 —— 不可整个目录直接推。")
        print("  可选：(A) 只上传通用方法论技能  (B) 脱敏后公开  (C) 私有库全量  (D) 不传")
    else:
        print("结论：未发现泄露点（仍建议排除 ARCHIVE 目录）。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
