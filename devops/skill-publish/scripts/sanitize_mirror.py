#!/usr/bin/env python3
"""sanitize_mirror.py — 给 git 历史做脱敏镜像，推到远端。

## 为什么需要它

`~/.hermes/skills` 既是**活的技能库**（技能必须保留真路径/真 IP 才能在本机跑）
又是**本地版本库**。所以不能就地改写它的历史 —— 改了技能就跑不动。

做法：克隆一份镜像，在镜像里把**每个提交的每棵树**都过一遍脱敏，
再 force-push 覆盖远端。本地保持真值不动。

## 用法

    python3 sanitize_mirror.py --src ~/.hermes/skills --dst /tmp/skills-mirror
    cd /tmp/skills-mirror && git remote set-url origin <私有库URL> && git push -f origin master

## 两个必须知道的点

1. **force-push 会重写远端历史**。远端已有的提交会消失 —— 这正是目的
   （旧提交里带着真值）。推前先备份远端或确认本地就是唯一权威副本。
2. **每个提交都要脱敏，不只是 HEAD**。只清 HEAD 的话，`git log -S <真值>` 照样
   能把真值从历史里挖出来 —— 2026-10-12 实测：远端 9 个提交里有 3 个含 QQ ID。
"""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SKILL_SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SKILL_SCRIPTS))
import sanitize_for_public as S  # noqa: E402


def git(*args, cwd=None, check=True):
    r = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    if check and r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed:\n{r.stderr}")
    return r.stdout


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True, help="源仓库（活的工作目录，只读）")
    ap.add_argument("--dst", required=True, help="镜像目录（会被 rm -rf 重建）")
    ap.add_argument("--keep-origin", action="store_true",
                    help="保留源仓库的 origin（默认清掉，避免误推）")
    args = ap.parse_args()

    src = Path(args.src).expanduser().resolve()
    dst = Path(args.dst).expanduser().resolve()
    if dst.exists():
        shutil.rmtree(dst)

    print(f"[mirror] 克隆 {src} -> {dst}")
    git("clone", "--no-hardlinks", "--quiet", str(src), str(dst))

    # 镜像里清掉 origin：防止脱敏前误推
    if not args.keep_origin:
        git("remote", "remove", "origin", cwd=dst, check=False)

    # 每个提交的每棵树都过脱敏。filter-branch 的 tree-filter 在 `.git-rewrite/t`
    # 临时检出目录里跑，所以 helper 必须放在**仓库外**并用绝对路径调用
    # （放仓库根目录会随 tree-filter 的检出被覆盖/找不到 —— 2026-10-12 实测踩过）。
    helper = Path(tempfile.gettempdir()) / "hermes_sanitize_tree_step.py"
    helper.write_text(
        _TREE_STEP.replace("__SCRIPTS__", str(SKILL_SCRIPTS)), encoding="utf-8")

    print("[mirror] 开始逐提交脱敏（54 个提交，几分钟）")
    r = subprocess.run(
        ["git", "filter-branch", "-f", "--tree-filter",
         f"python3 {helper}", "--prune-empty", "--", "HEAD"],
        cwd=dst, capture_output=True, text=True,
        env={**os.environ, "FILTER_BRANCH_SQUELCH_WARNING": "1"},
    )
    print(r.stdout[-2000:] if r.stdout else "")
    if r.returncode != 0:
        print("[mirror] filter-branch 失败：", r.stderr[-3000:], file=sys.stderr)
        return 1

    helper.unlink(missing_ok=True)
    git("add", "-A", cwd=dst)
    git("commit", "-q", "-m", "mirror: drop sanitizer helper", cwd=dst, check=False)

    # 收尾：filter-branch 留的备份引用会带着**未脱敏**的对象，必须清掉
    git("for-each-ref", "--format=%(refname)", "refs/original/", cwd=dst, check=False)
    git("update-ref", "-d", "refs/original/refs/heads/master", cwd=dst, check=False)
    git("reflog", "expire", "--expire=now", "--all", cwd=dst, check=False)
    git("gc", "--prune=now", "--quiet", cwd=dst, check=False)

    n = git("rev-list", "--count", "HEAD", cwd=dst).strip()
    print(f"[mirror] 完成：{n} 个提交")
    print(f"[mirror] 下一步：cd {dst} && git remote add origin <URL> && git push -f origin HEAD")
    return 0


# tree-filter 步骤：在检出树里就地脱敏。必须自包含（filter-branch 每个提交都重跑）。
_TREE_STEP = '''\
import os, sys
from collections import Counter
from pathlib import Path
sys.path.insert(0, r"__SCRIPTS__")
import sanitize_for_public as S

root = Path(".")
for p in sorted(root.rglob("*")):
    if ".git/" in str(p):
        continue
    rel = p.relative_to(root)
    # **软链检查必须在 is_file() 之前**：软链指向目录时 is_file() 返回 False，
    # 指向库外时更是直接断链 —— 放在 is_file() 后面就永远到不了，软链会原样留在库里
    # （2026-10-12 实测：加了 symlink 分支但位置不对，6 个软链一个没清掉）。
    if p.is_symlink():
        p.unlink()
        continue
    if not p.is_file():
        continue
    # 排除目录（归档/备份/运行态/克隆）——与公开版同一套规则
    if any(part in S.EXCLUDE_DIRS for part in rel.parts):
        p.unlink()
        continue
    if rel.name in S.EXCLUDE_NAMES or rel.name.startswith(S.EXCLUDE_PREFIX_FILES):
        p.unlink()
        continue
    # .bak / .bak-* / .bak.* 一律出库：备份文件本身就该在 .gitignore 里，
    # 历史里已经进来的（如 INDEX.md.bak-audit-20260918）必须在这里清掉。
    if ".bak" in rel.name:
        p.unlink()
        continue
    # **指向库外的软链一律剔除**（2026-10-12）：库里有 6 个软链指向
    # `~/.agents/skills/`（插件装的第三方技能，如 ef-* / obsidian-*）。
    # 它们在 GitHub 上是断链，而且**是别人的技能**，不该进我们的库 ——
    # 与 NESTED_REPOS 同一条原则。剔除而不是解引用：解引用等于把别人的东西抄一份。
    if not S.is_texty(p):
        continue
    # **必须用 surrogateescape 读写**：文件里只要有一个非法 UTF-8 字节，
    # `read_text(encoding="utf-8")` 就抛异常 → except 直接 continue →
    # **整个文件静默跳过脱敏**（2026-10-12 实测：INDEX.md.bak-audit-20260918
    # 含一个坏字节，于是里面的真机 IP 原样留在历史里）。
    # 读不了 ≠ 干净 —— 读不了必须仍然尽量脱敏，而不是当它不存在。
    try:
        text = p.read_text(encoding="utf-8", errors="surrogateescape")
    except OSError:
        continue
    clean = S.sanitize_text(text, Counter())
    clean = S.self_redact(clean)
    if clean != text:
        p.write_text(clean, encoding="utf-8", errors="surrogateescape")
'''

if __name__ == "__main__":
    sys.exit(main())
