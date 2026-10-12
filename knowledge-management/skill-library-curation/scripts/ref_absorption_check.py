#!/usr/bin/env python3
"""分诊：源技能的内容是否已被逐字吸收进目标技能的 references/。

用法:
    python3 ref_absorption_check.py <源技能目录或SKILL.md> <目标技能里的ref文件.md>

输出:
    only-in-src: N   源里有、ref 里没有的行数（>0 = 还有真内容没吸收）
    only-in-ref: M   ref 里多出来的行（通常就是「合并来源」表头那几行）

判读:
    N == 0   → 源已逐字冗余。剩余工作 = 归档源目录 + 结构 pass + 修活指针，
               不需要再读一遍源正文重新整合。
    N 很大   → 真·未吸收，走完整 union merge。
    0 < N 小 → 逐行定性（多半只是路径改写或表头差异），别只看条数下结论。
"""
import difflib
import sys
from pathlib import Path


def skill_md(p: str) -> Path:
    p = Path(p)
    return p / "SKILL.md" if p.is_dir() else p


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__)
        return 2
    src, ref = skill_md(sys.argv[1]), Path(sys.argv[2])
    for f in (src, ref):
        if not f.is_file():
            print(f"missing file: {f}")
            return 2
    a = [l.rstrip() for l in src.read_text(encoding="utf-8").splitlines()]
    b = [l.rstrip() for l in ref.read_text(encoding="utf-8").splitlines()]
    d = [x for x in difflib.unified_diff(a, b, lineterm="", n=0)
         if x[:1] in "+-" and not x.startswith(("+++", "---"))]
    lost = [x for x in d if x[0] == "-"]
    extra = [x for x in d if x[0] == "+"]
    print(f"src : {src}  ({len(a)} lines)")
    print(f"ref : {ref}  ({len(b)} lines)")
    print(f"only-in-src: {len(lost)}   only-in-ref: {len(extra)}")
    if lost:
        print("\n--- 源里有、ref 里没有（逐行定性，别只看条数）---")
        for x in lost[:40]:
            print("  " + x[:160])
    else:
        print("\nVERDICT: 源已逐字冗余 → 归档源 + 结构 pass + 修活指针，不用重新整合内容")
    return 0


if __name__ == "__main__":
    sys.exit(main())
