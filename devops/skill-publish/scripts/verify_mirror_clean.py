#!/usr/bin/env python3
"""verify_mirror_clean.py — 彻底验证 git 仓库【全部历史对象】里没有真值。

为什么不能只用 `git log -S`：`-S` 是「字符串出现次数发生变化」的提交，
只能找到**增删点**；某个提交改了一处、另一处仍在的形态它不一定报。
要断言「历史里挖不出来」，必须把**每个 blob 的每个字节**都过一遍。

用法：
    python3 verify_mirror_clean.py --repo /tmp/skills-mirror
    python3 verify_mirror_clean.py --repo /tmp/skills-mirror --json out.json
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

# 复扫模式从本机配置生成 —— 别把真值硬写在这份脚本里
# （这份文件自己也会进公开库，硬写真值就是二次泄露）。
SKILL_SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SKILL_SCRIPTS))
import sanitize_for_public as S  # noqa: E402


def patterns():
    out = [("SUBS", p.pattern) for p, _ in S.SUBS]
    for lit, _ in S.sensitive_literals():
        out.append(("LIT", lit))
    out.append(("PHONE", S.PHONE.pattern))
    return out


# 我们自己写进去的占位符（脱敏器的替换目标）。它们**本来就该出现在产物里**，
# 不是残留 —— 验证时必须豁免，否则永远报「不干净」，久了就没人看报告了。
# 判定用「匹配到的值是否全是占位形态」，而不是「正则原文是否等于某条」：
# 同一条正则既会匹配真值也会匹配占位符，必须看**匹配结果**。
PLACEHOLDER_VALUES = {"192.168.99.X", "172.31.99.X", "10.99.99.X",
                      "<QQ_ID>", "<TELEGRAM_ID>", "$HOME", "<user>@",
                      "<hostname>", "<win-host>", "VAULT", "<PHONE>",
                      "<ID_CARD>", "<CARD_NO>", "<ADDRESS>", "<EMAIL>",
                      "<ACCOUNT>", "<PRIVATE_KEY_BLOCK>", "<gh-account>"}


def _only_placeholders(found: list[str]) -> bool:
    return bool(found) and all(v in PLACEHOLDER_VALUES for v in found)


def _parse_batch(stream: bytes, order: list[str]):
    """把 `git cat-file --batch` 的输出拆成 (sha, content)。

    输出格式：`<sha> blob <size>\\n<size 字节内容>\\n`，重复。
    必须按 size 精确切，不能用分隔符 —— 内容本身可能含任意字节。
    """
    pos = 0
    for sha in order:
        nl = stream.find(b"\n", pos)
        if nl < 0:
            return
        header = stream[pos:nl].decode("utf-8", "replace").split()
        if len(header) < 3 or header[1] != "blob":
            pos = nl + 1
            continue
        size = int(header[2])
        content = stream[nl + 1:nl + 1 + size].decode("utf-8", "surrogateescape")
        pos = nl + 1 + size + 1
        yield sha, content


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--json", default="")
    args = ap.parse_args()

    repo = Path(args.repo).expanduser().resolve()
    pats = patterns()

    # 全部对象（含悬挂对象：filter-branch 的 refs/original 若没清干净会在这里露出来）
    ids = subprocess.run(
        ["git", "cat-file", "--batch-all-objects", "--batch-check=%(objectname) %(objecttype)"],
        cwd=repo, capture_output=True, text=True, check=True,
    ).stdout.splitlines()
    blobs = [l.split()[0] for l in ids if l.endswith(" blob")]
    print(f"[verify] {repo}: {len(ids)} 个对象，其中 blob {len(blobs)} 个")

    # 分批 cat-file，避免命令行过长。
    # **必须用 bytes 读**：仓库里有二进制 blob（png/字体/压缩数据），
    # `text=True` 会在解码时抛 UnicodeDecodeError（2026-10-12 实测）。
    # **必须剥掉 batch 头再扫**：`cat-file --batch` 的输出里每段前面有
    # `<sha1> blob <size>` 头，SHA-1 十六进制串里含 16-19 位连续数字，
    # 会被「卡号」规则命中 —— 2026-10-12 实测报了 2 处这种假阳性。
    # 检查器扫到自己的输出格式 = 又一次「守卫自己不做守卫」。
    #
    # 用 **surrogateescape** 解码：历史里有含非法 UTF-8 字节的文件，
    # 严格解码会抛异常或整段丢失，从而**漏检**（2026-10-12 实测）。
    hits = {}
    BATCH = 300
    for i in range(0, len(blobs), BATCH):
        chunk = blobs[i:i + BATCH]
        r = subprocess.run(["git", "cat-file", "--batch"],
                           cwd=repo, input="\n".join(chunk).encode(),
                           capture_output=True)
        for sha, content in _parse_batch(r.stdout, chunk):
            for kind, pat in pats:
                try:
                    found = re.findall(pat, content)
                except re.error:
                    continue
                # 只匹配到我们自己的占位符 = 正常，不算残留
                if not found or _only_placeholders(found):
                    continue
                # 混了真值：把真值那部分单独记下来（占位符不进样本）
                real = [v for v in found if v not in PLACEHOLDER_VALUES]
                key = pat
                if key not in hits:
                    hits[key] = {"kind": kind, "count": 0, "blobs": [],
                                 "sample": sorted(set(real))[:3]}
                hits[key]["count"] += len(real)
                if sha not in hits[key]["blobs"]:
                    hits[key]["blobs"].append(sha)
        print(f"  {i + len(chunk)}/{len(blobs)}", end="\r", flush=True)

    print()
    if hits:
        print(f"[verify] ✗ 发现 {len(hits)} 类残留：")
        for pat, info in hits.items():
            print(f"    [{info['kind']}] {pat[:60]}  x{info['count']}  样本={info['sample']}")
    else:
        print(f"[verify] ✓ {len(pats)} 条规则全过 —— 全部历史对象里无真值")

    if args.json:
        Path(args.json).write_text(json.dumps(hits, ensure_ascii=False, indent=2),
                                   encoding="utf-8")
    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main())
