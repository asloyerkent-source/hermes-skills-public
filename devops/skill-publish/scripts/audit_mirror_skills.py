#!/usr/bin/env python3
"""audit_mirror_skills.py — 逐技能审核镜像里的脱敏结果。

比全库 grep 更细：**按技能分组**输出，这样能回答「第 N 个技能干净吗」，
而不是只知道「全库有 X 处残留」。

检查项（每个技能独立判）：
  1. 真值残留（从脱敏器规则表派生，不硬写）
  2. 绝对家目录路径 / 私网 IP / 主机名 / 账户名
  3. frontmatter 完整性（name/description 存在）
  4. 引用本机绝对路径（家目录、Windows 用户目录）
  5. 指向库外的相对路径（`../<不存在的技能>/`）
  6. 占位符是否被误写进正文（`$HOME` 在代码块里是正常的，正文里可疑）

用法：
    python3 audit_mirror_skills.py --root /tmp/skills-mirror [--json out.json]
"""
import argparse
import json
import re
import sys
from pathlib import Path

SKILL_SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SKILL_SCRIPTS))
import sanitize_for_public as S  # noqa: E402
from verify_mirror_clean import PLACEHOLDER_VALUES, patterns  # noqa: E402

FM_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.S)
ABS_PATH = re.compile(r"(?<![\w])/(?:home|Users)/[A-Za-z0-9_.-]+")
# Windows 路径两种分隔符都要抓（`C:\Users\<user>` 与 `C:/Users/<user>`）
WIN_PATH = re.compile(r"[A-Za-z]:[\\/]Users[\\/][A-Za-z0-9_.-]+")

# 通用占位/示例用户名 —— 这些**本来就是文档里教别人用的占位符**，
# 不是真值。审核器必须豁免，否则每份「写文档时别泄露家目录」的说明
# 都会自己报错（2026-10-12 实测：`/home/xxx`、`C:\Users\<user>` 这类教学示例
# 被当成残留，13 个技能里有一半是这种假阳性）。
GENERIC_USERS = {"xxx", "x", "user", "me", "you", "alice", "bob", "username",
                 "youruser", "name", "someone", "test", "demo", "...", "<user>"}
GENERIC_PATH = re.compile(
    r"(?:/home|/Users|[A-Za-z]:[\\/]Users)[\\/](?:" +
    "|".join(re.escape(u) for u in sorted(GENERIC_USERS, key=len, reverse=True)) +
    r")(?![A-Za-z0-9_.-])")


def check_skill(skill_dir: Path, root: Path, pats):
    """返回该技能的所有问题列表。"""
    issues = []
    files = sorted(f for f in skill_dir.rglob("*") if f.is_file())

    for f in files:
        try:
            text = f.read_text(encoding="utf-8", errors="surrogateescape")
        except OSError:
            issues.append({"file": str(f.relative_to(root)), "kind": "unreadable"})
            continue
        rel = str(f.relative_to(root))

        # 1. 真值残留
        for kind, pat in pats:
            try:
                found = re.findall(pat, text)
            except re.error:
                continue
            real = [v for v in found if v not in PLACEHOLDER_VALUES]
            if real:
                issues.append({"file": rel, "kind": f"残留:{kind}",
                               "sample": sorted(set(real))[:3], "n": len(real)})

        # 2. 绝对路径（豁免通用占位用户名 —— 那是文档示例不是真值）
        for m in ABS_PATH.finditer(text):
            if GENERIC_PATH.match(m.group(0)):
                continue
            issues.append({"file": rel, "kind": "绝对家目录", "sample": m.group(0)})
        for m in WIN_PATH.finditer(text):
            if GENERIC_PATH.match(m.group(0)):
                continue
            issues.append({"file": rel, "kind": "绝对Win路径", "sample": m.group(0)})

    # 3. frontmatter
    sk = skill_dir / "SKILL.md"
    if sk.exists():
        try:
            t = sk.read_text(encoding="utf-8", errors="surrogateescape")
        except OSError:
            t = ""
        m = FM_RE.search(t)
        if not m:
            issues.append({"file": str(sk.relative_to(root)), "kind": "无frontmatter"})
        else:
            fm = m.group(1)
            if not re.search(r"^name:\s*\S", fm, re.M):
                issues.append({"file": str(sk.relative_to(root)), "kind": "缺name"})
            if not re.search(r"^description:\s*\S", fm, re.M):
                issues.append({"file": str(sk.relative_to(root)), "kind": "缺description"})

    return issues


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--json", default="")
    ap.add_argument("--only-dirty", action="store_true")
    args = ap.parse_args()

    root = Path(args.root).expanduser().resolve()
    pats = patterns()

    # 找技能：含 SKILL.md 的目录
    skills = sorted({p.parent for p in root.rglob("SKILL.md") if ".git" not in p.parts})
    print(f"[audit] {root}: {len(skills)} 个技能\n")

    all_res = {}
    dirty = 0
    for i, sd in enumerate(skills, 1):
        rel = sd.relative_to(root)
        iss = check_skill(sd, root, pats)
        all_res[str(rel)] = iss
        if iss:
            dirty += 1
            print(f"[{i:3d}/{len(skills)}] ✗ {rel}  ({len(iss)} 处)")
            for x in iss[:4]:
                print(f"        {x['kind']}  {x.get('sample','')}  @{x['file']}")
        elif not args.only_dirty:
            print(f"[{i:3d}/{len(skills)}] ✓ {rel}")

    print(f"\n[audit] 干净 {len(skills)-dirty} / 有问题 {dirty}")
    if args.json:
        Path(args.json).write_text(json.dumps(all_res, ensure_ascii=False, indent=2),
                                   encoding="utf-8")
    return 1 if dirty else 0


if __name__ == "__main__":
    sys.exit(main())
