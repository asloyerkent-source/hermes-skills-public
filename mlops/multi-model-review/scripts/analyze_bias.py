#!/usr/bin/env python3
"""汇总 judge_bias_result.json，做基本统计判读（含精确二项检验）。"""
import json
from math import comb
from pathlib import Path

d = json.load(open("$HOME/.hermes/cache/scratch/judge_bias_result.json", encoding="utf-8"))

rows = []
for m in d:
    for c in m["cells"]:
        if c:
            rows.append({"model": m["model"], **c})

print(f"有效观测: {len(rows)}\n")

def binom_p(k, n, p=0.5):
    """P(X <= k) 精确二项"""
    return sum(comb(n, i) * p**i * (1-p)**(n-i) for i in range(k+1))

for variant in ("obvious", "subtle"):
    sub = [r for r in rows if r["variant"] == variant]
    n = len(sub)
    pad = sum(1 for r in sub if r["chosen"] == "padded")
    apos = sum(1 for r in sub if r["letter"] == "A")
    print(f"--- {variant} (n={n}) ---")
    print(f"  注水被选: {pad}/{n}")
    if n:
        p = binom_p(pad, n)
        print(f"    若判官对长度不敏感(p=0.5)，观测到 <= {pad} 次的概率 = {p:.4f}"
              f"  {'→ 可拒绝「无明显长度偏好」假设' if p < 0.05 else '→ 样本不足以拒绝'}")
    print(f"  选位置A: {apos}/{n}")
    if n:
        p2 = min(binom_p(apos, n), 1 - binom_p(apos - 1, n) if apos > 0 else 1)
        print(f"    位置A 占比 {apos/n:.0%}")

n_all = len(rows)
pad_all = sum(1 for r in rows if r["chosen"] == "padded")
a_all = sum(1 for r in rows if r["letter"] == "A")
print(f"\n=== 全部 {n_all} 轮 ===")
print(f"  注水被选: {pad_all}/{n_all} = {pad_all/n_all:.0%}")
print(f"  选位置A : {a_all}/{n_all} = {a_all/n_all:.0%}")
print(f"  若位置无偏(p=0.5)，观测到 >= {a_all} 次选A的概率 = {1-binom_p(a_all-1, n_all):.4f}")

# 唯一那例注水胜出，看它是不是「跟着位置走」
print("\n=== 逐模型看是否存在「跟位置不跟内容」的模式 ===")
for m in d:
    cs = [c for c in m["cells"] if c]
    if len(cs) < 3:
        print(f"  {m['model']:<18} 有效样本不足({len(cs)})")
        continue
    letters = "".join(c["letter"] for c in cs)
    choices = "".join("C" if c["chosen"] == "concise" else "P" for c in cs)
    flag = "  ⚠️ 同字母连选" if len(set(letters)) == 1 and len(cs) >= 3 else ""
    print(f"  {m['model']:<18} 字母序列={letters}  内容序列={choices}(C=精简,P=注水){flag}")
