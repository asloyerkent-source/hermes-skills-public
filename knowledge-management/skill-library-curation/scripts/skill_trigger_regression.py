#!/usr/bin/env python3
"""技能触发可读性回归测试 —— 描述里有没有「用户真会说的词」。

⚠️ **本脚本不测唤醒率。** 它只做一件事：拿一组真实用户话术去查
期望技能的 description 有没有出现那些话术里的词。得不出「模型实际会不会
调用这个技能」——那要真调一次 API 看加载了哪些技能。
脚本名与能力不符时，人会把输出当更大的那个结论用，所以这句写在 docstring 里。

判据用**显式关键词表**，不用字符相似度（整词 `in` 与 n-gram 在中文上都会假阴性：
「机器人不回复了」vs「机器人不回复」差一个字；「改配置」这种 3 字词切不出来）。
显式表可读、可审、可改；阈值不可读，改参数就等于换了个判据。

用法：
  python3 skill_trigger_regression.py --verbose   # 显示每条命中详情
退出码：有 miss → 1（唤醒可疑）；全过 → 0；读数通道坏 → 2。
"""
import glob
import os
import re
import sys

SKILLS_DIR = os.path.expanduser("~/.hermes/skills")

# (真实用户话术, 期望技能, 该技能 description 里必须出现的词)
# 话术取自实际收到过的原话；关键词逐条对过 description 原文，不是凭印象写的。
CASES = [
    ("改一下 config.yaml",            "execution-discipline",       ["改配置", "动手"]),
    ("报错了帮我查一下",              "systematic-debugging",       ["故障", "bug"]),
    ("机器人不回复了",                "hermes-gateway-troubleshoot", ["机器人不回复", "网关"]),
    ("这个数不太对，再核一遍",        "measurement-integrity",      ["检查脚本", "探针"]),
    ("看图",                          "local-vlm",                  ["看图"]),
    ("建双机连接",                    "dual-machine-hermes-connect", ["建双机连接"]),
    ("同步文件",                      "dual-machine-sync",          ["双机同步"]),
    ("存进 vault",                    "knowledge-vault-ops",        ["vault", "知识库"]),
    ("搜一下俄罗斯的AI动态",          "china-briefing",             ["调研", "搜索"]),
    ("我拿不准，你给个独立意见",      "doubt-driven-development",   ["独立审稿"]),
    ("重新裁剪点东西",                "safe-file-organization",     ["清理", "归档"]),
    ("存档到期了吗",                  "hermes-memory-ops",          ["记忆"]),
    ("审一下这段源码有没有洞",        "security-audit",             ["源码"]),
    ("派活给Pi写代码",                "coding-delegation",          ["派 Pi", "代码"]),
]


def load_descriptions():
    """多深度 glob —— 库内技能在 category/skill/SKILL.md，单层模式会静默漏扫。"""
    out = {}
    patterns = [f"{SKILLS_DIR}/*/*/SKILL.md",
                f"{SKILLS_DIR}/*/SKILL.md",
                f"{SKILLS_DIR}/*/*/*/SKILL.md"]
    for pat in patterns:
        for f in glob.glob(pat):
            t = open(f, encoding="utf-8", errors="ignore").read()
            m = re.search(r"^name:\s*(.+)$", t, re.M)
            d = re.search(r"^description:\s*(.+)$", t, re.M)
            if m and d:
                out[m.group(1).strip()] = d.group(1).strip()
    return out


def main():
    verbose = "--verbose" in sys.argv
    descs = load_descriptions()

    # 读数通道自检：读不到或读太少 ⇒ 后面所有百分比都只是这几个的，别往下算
    if len(descs) < 50:
        print(f"ERROR: 只读到 {len(descs)} 个 description（应约 85），读数通道坏了")
        return 2

    ok, misses = 0, []
    for text, expect, words in CASES:
        d = descs.get(expect)
        if d is None:
            misses.append((text, expect, ["<技能不在库里>"]))
            if verbose:
                print(f"  MISS {text!r:28s} →{expect} 不在库里")
            continue
        absent = [w for w in words if w not in d]
        if absent:
            misses.append((text, expect, absent))
            if verbose:
                print(f"  MISS {text!r:28s} →{expect} 缺触发词 {absent}")
        else:
            ok += 1
            if verbose:
                print(f"  ok   {text!r:28s} → {expect}")

    print(f"\n读到 {len(descs)} 个技能的 description")
    print("=" * 56)
    print(f"触发词完整度: {ok}/{len(CASES)}")

    if misses:
        print("\n唤醒可疑（描述与真实话术用词不符）:")
        for text, expect, absent in misses:
            print(f"  ·{text!r:30s}期望 {expect} 缺 {absent}")
        print("\n处置：给 description 补这些词，或确认这些词确实不该触发（改本表）。")
        print("失败条目先分「被测物缺」与「本表期望写错」——后者不该去改 description。")
        return 1

    print("⚠️ 这是**描述可读性**，不是唤醒率。真唤醒率要真调 API 看加载了哪些技能。")
    return 0


if __name__ == "__main__":
    sys.exit(main())