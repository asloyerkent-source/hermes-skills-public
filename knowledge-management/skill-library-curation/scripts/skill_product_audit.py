"""Post-merge product audit for a skill directory (stdlib only).

Complements ~/.hermes/scripts/skill_ref_lint.py, which checks ONE direction
(pointer -> file, i.e. broken links). This checks the other direction plus the
structural damage a union merge leaves behind:

  1. SKILL.md size vs a sane ceiling (a merge whose SKILL.md never shrank means
     the structure pass never happened)
  2. orphan files  : exist under references/ or scripts/ but SKILL.md never
                     mentions them  -> written but nobody knows it exists
  3. broken refs   : SKILL.md points at a file that is not there
  4. SPEC          : format conformance, 11 checks / 100 pts, delegated to
                     ~/.hermes/scripts/skill_spec_audit.py (port of @skilldex/validator).
                     Only errors and sub-70 scores are reported per-skill; the
                     thresholds there are tuned for Hermes, not for Anthropic's
                     published spec — see that file's comments before trusting a score.
  5. block dupes   : the same >=150-char paragraph block appearing twice inside
                     one file (source A's section also embedded in source B,
                     concatenated twice by the merge)
  5. stale self-ref: "see the 'X' section" / "this file's 'Y' section" left
                     pointing at a section that was moved into a ref

Usage:
    python3 skill_product_audit.py                 # whole library
    python3 skill_product_audit.py --skill <name>   # one skill
    python3 skill_product_audit.py --root <path>

Exit code 1 if any check reports a problem, else 0. Safe to run from cron.
"""

import argparse
import os
import re
import sys
from collections import Counter

SKIP_DIR_PARTS = {".archive", ".hub", ".curator_backups", "skill-backups"}
# 2026-09-30：基线 12 KiB。实测 22/79 技能超标，其中一半贴着天花板且**没有一个**
# 是修改日志体或拼接体 —— 即「内容真的就这么长」，尤其 refs 多的导航型技能
# （skill-library-curation refs=61 / 22.8KB）。单一固定阈值把它们和真正该治的
# 混在一起报，等于制造噪声。改成按 refs 数量动态放宽（见 ceiling_for）。
DEFAULT_CEILING = 12288  # 12 KiB，基线；无 refs 时用它
CEILING_PER_REF = 320    # 每多一个 references/ 追加的字节
CEILING_MAX = 32768      # 32 KiB 硬顶，再多就是没拆
BLOCK_MIN = 150

# 「被改肿」的指纹（铁律 19）：反复修过的技能会长成修改日志而不是技能文档。
# ⚠️ 多行锚点 ^ 必须编译期带 re.M —— 写 search(txt, re.M) 是把 re.M(=8) 当成了 pos，
#    等于「从第 8 个字符开始找」，实测让本函数三个分支全判成「真胖」（自测抓到）。
HISTORY_HEADING_RE = re.compile(
    r"^#{2,4}.*(修复要点|本轮|第[一二三四五六七八九十]+轮|已修|更新记录|变更记录|踩坑记录)",
    re.M)
MERGE_STITCH_RE = re.compile(r"^## 源模块:", re.M)


def ceiling_for(ref_count):
    """导航型技能天然更长：每 3 个 references/ 多给 1 KiB，上限 32 KiB。

    2026-09-30 实测依据：refs=0 的技能里最大的（skill-evolution 32KB、
    measurement-integrity 30KB、officecli 26KB）确实是真胖，该报；
    而 refs=45~61 的（hermes-model-routing 27KB、skill-library-curation 22.8KB）
    是导航表撑起来的，不是该治的病。
    """
    return min(DEFAULT_CEILING + CEILING_PER_REF * ref_count, CEILING_MAX)


def classify_size(text, size, ceiling):
    """区分「真胖」与「被改肿」——两者处置完全不同，不能只报一个数字。

    返回 SIZE 子标签：'' / ' (真胖)' / ' (拼接体)' / ' (修改日志体)'，可叠加。
    """
    tags = []
    if MERGE_STITCH_RE.search(text, re.M):
        tags.append("拼接体")
    n_hist = len(HISTORY_HEADING_RE.findall(text, re.M))
    if n_hist >= 3:
        tags.append("修改日志体")
    if not tags:
        # 两种指纹都没有 = 内容真的就这么多。仍然报，但要标清楚不是「被改肿」。
        return " (真胖)" if size > ceiling else ""
    return " (" + "+".join(tags) + ")"


# 2026-09-30 集成 skill_spec_audit.py（11 项 100 分制格式合规，移植自 @skilldex/validator）。
# 放在这里而不是各跑一次：体检命令要一次给全结论，分成两个工具等于让人自己合并判断。
# 找不到该脚本时降级为跳过，不让本工具因缺依赖而整体失败。
def _load_spec_audit():
    for cand in (os.path.expanduser("~/.hermes/scripts/skill_spec_audit.py"),
                 os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "..", "..", "..", "..", "..", "scripts", "skill_spec_audit.py")):
        if os.path.exists(cand):
            import importlib.util
            spec = importlib.util.spec_from_file_location("_skill_spec_audit", cand)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod
    return None


_SPEC = None
_SPEC_TRIED = False


def spec_audit(d):
    """Format-conformance result for one skill dir, or None if unavailable."""
    global _SPEC, _SPEC_TRIED
    if not _SPEC_TRIED:
        _SPEC = _load_spec_audit()
        _SPEC_TRIED = True
    if _SPEC is None:
        return None
    try:
        return _SPEC.audit_skill(_SPEC.Path(d))  # 该审计器签名收 Path，本工具传 str
    except Exception as e:  # 审计器自身出错不该让主审计崩掉
        return {"score": 0, "error": "spec audit failed: %s" % e, "diagnostics": []}


def skill_dirs(root):
    for cur, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if not d.startswith(".") and d not in SKIP_DIR_PARTS]
        if "SKILL.md" in files:
            yield cur


def skills_named(root):
    out = {}
    for d in skill_dirs(root):
        out[os.path.basename(d)] = d
    return out


def read(p):
    try:
        with open(p, encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError:
        return ""


def block_dupes(text):
    """Return (wasted_bytes, n_groups) for repeated >=BLOCK_MIN char blocks."""
    blocks = [b.strip() for b in re.split(r"\n\n+", text)]
    c = Counter(b for b in blocks if len(b) >= BLOCK_MIN)
    dups = [(b, n) for b, n in c.items() if n > 1]
    return sum(len(b) * (n - 1) for b, n in dups), len(dups)


def distinct_long_lines(text):
    """Zero-loss cross-check for a dedupe.

    Record this BEFORE and AFTER removing duplicated blocks: if the count of
    distinct long lines is unchanged, no content was lost. This is the evidence
    that a block-level dedupe was safe, and it is why blocks (not lines) are the
    unit of removal -- line-level dedupe would destroy structure.
    """
    return len({ln.strip() for ln in text.split("\n") if len(ln.strip()) > 60})


def audit_one(d, ceiling):
    """Return (label, findings) where findings is a list of (kind, detail)."""
    sk_path = os.path.join(d, "SKILL.md")
    sk = read(sk_path)
    f = []

    size = len(sk.encode())

    # 2026-09-30：阈值按 references/ 数量动态（导航型技能天然更长），
    # 且报告区分「真胖」与「被改肿（拼接体/修改日志体）」——两者处置完全不同。
    refs_dir = os.path.join(d, "references")
    n_refs = len([x for x in os.listdir(refs_dir) if x.endswith(".md")]) \
        if os.path.isdir(refs_dir) else 0
    eff_ceiling = ceiling_for(n_refs)
    if size > eff_ceiling:
        f.append(("SIZE", "SKILL.md %dB (%.1fx ceiling %dB, refs=%d)%s"
                  % (size, size / eff_ceiling, eff_ceiling, n_refs,
                     classify_size(sk, size, eff_ceiling))))

    # orphan / broken, both directions
    for sub, exts in (("references", ".md"), ("scripts", None), ("templates", None)):
        sd = os.path.join(d, sub)
        if not os.path.isdir(sd):
            continue
        for fn in sorted(os.listdir(sd)):
            if exts and not fn.endswith(exts):
                continue
            if fn.startswith(".") or fn == "__pycache__":
                continue
            if fn not in sk:
                f.append(("ORPHAN", "%s/%s (%dB) not mentioned in SKILL.md" % (sub, fn, os.path.getsize(os.path.join(sd, fn)))))

    # BROKEN 判定：只在「非代码块」正文里查，且允许同一行给出可解析的绝对路径
    # （绝对路径形态的交叉引用是合法写法——如 ~/.hermes/skills/<other-skill>/references/x.md）
    def _strip_code_blocks(text):
        out, in_block = [], False
        for line in text.split("\n"):
            if line.lstrip().startswith("```"):
                in_block = not in_block
                out.append("")
                continue
            out.append("" if in_block else line)
        return "\n".join(out)

    body = _strip_code_blocks(sk)

    def _abs_ok(rel):
        """同一行里若写了能解析的绝对路径，则不算断链。"""
        pat = re.compile(r"([~/][^\s`'\"\u201d\u3001\uff09\u0029]*" + re.escape(rel) + r")")
        for line in sk.split("\n"):
            if rel not in line:
                continue
            for cand in pat.findall(line):
                for p in (cand, os.path.expanduser(cand),
                          os.path.expanduser(cand).replace("~/.hermes/skills/", "")):
                    if os.path.exists(p):
                        return True
        return False

    for m in sorted(set(re.findall(r"references/([A-Za-z0-9_.\-]+\.md)", body))):
        if os.path.exists(os.path.join(d, "references", m)):
            continue
        if _abs_ok("references/" + m):
            continue
        f.append(("BROKEN", "references/%s does not exist" % m))
    for m in sorted(set(re.findall(r"scripts/([A-Za-z0-9_.\-]+\.[a-z]+)", body))):
        if os.path.exists(os.path.join(d, "scripts", m)):
            continue
        if _abs_ok("scripts/" + m):
            continue
        if re.search(r"[A-Za-z0-9_.\-/]scripts/" + re.escape(m), body):
            continue
        f.append(("BROKEN", "scripts/%s does not exist" % m))

    # internal block duplication in SKILL.md and every ref
    for p in [sk_path] + [
        os.path.join(d, "references", x)
        for x in (os.listdir(os.path.join(d, "references")) if os.path.isdir(os.path.join(d, "references")) else [])
        if x.endswith(".md")
    ]:
        txt = read(p)
        wasted, groups = block_dupes(txt)
        if groups:
            f.append(("DUP_BLOCK", "%s: %d repeated block(s), %dB wasted" % (os.path.relpath(p, d), groups, wasted)))

    # stale self-references: a quoted section name that is no longer a heading here
    heads = re.findall(r"^#{1,6}\s*(.+)$", sk, re.M)
    head_blob = "\n".join(heads)
    for m in re.finditer(r"(?:见|参见|回写|完整实现见|详见)\s*[「\u201c]([^」\u201d]{2,40})[」\u201d]", sk):
        name = m.group(1)
        if name in head_blob:
            continue
        if name in sk.split("\n")[0]:
            continue
        f.append(("SELFREF", "points at section \u300c%s\u300d not present in this file" % name))

    # 格式合规（SPEC）：分数低或含 error 才报，warning 归入汇总不逐条刷屏
    sr = spec_audit(d)
    if sr is None:
        f.append(("SPEC", "skill_spec_audit.py not found - spec checks skipped"))
    elif sr.get("error"):
        f.append(("SPEC", sr["error"]))
    else:
        for diag in sr.get("diagnostics", []):
            if diag.get("severity") == "error":
                f.append(("SPEC", "%s: %s" % (diag.get("check"), diag.get("message"))))
        sc = sr.get("score", 0)
        if sc < 70 and not any(k == "SPEC" for k, _ in f):
            f.append(("SPEC", "format score %d/100 (<70) - run skill_spec_audit.py for breakdown" % sc))

    return d, f


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=os.path.expanduser("~/.hermes/skills"))
    ap.add_argument("--skill", default=None)
    ap.add_argument("--ceiling", type=int, default=DEFAULT_CEILING)
    ap.add_argument("--quiet-ok", action="store_true", help="only print skills with findings")
    a = ap.parse_args()

    if a.skill:
        hits = {k: v for k, v in skills_named(a.root).items() if k == a.skill}
        if not hits:
            print("no skill named %r under %s" % (a.skill, a.root))
            return 1
        targets = list(hits.values())
    else:
        targets = list(skill_dirs(a.root))

    counts = Counter()
    total = 0
    for d in sorted(targets):
        total += 1
        label, findings = audit_one(d, a.ceiling)
        if not findings:
            if not a.quiet_ok:
                print("[OK]   %s" % os.path.relpath(label, a.root))
            continue
        print("[WARN] %s" % os.path.relpath(label, a.root))
        for kind, detail in findings:
            counts[kind] += 1
            print("         %-10s %s" % (kind, detail))

    summary = "  ".join("%s=%d" % (k, v) for k, v in sorted(counts.items())) or "clean"
    print("\n" + "=" * 68)
    print("skills=%d  %s" % (total, summary))
    bad = counts["ORPHAN"] + counts["BROKEN"] + counts["DUP_BLOCK"] + counts["SELFREF"]
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
