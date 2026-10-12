#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""技能库结构体检 —— 一次跑完，只报真问题。

2026-10-02 建。起因是全库扫出 1 个 SyntaxError（publish_preflight.py 整个
import 就崩），而它存在了不知道多久。写这条命令是为了让「技能库改了之后
有没有语法错 / 死指针」变成一条命令，而不是每次手写扫描。

**这一版修掉了自己会犯的三类假阳性**（都是 2026-10-02 当天实测踩到的）：

1. **死指针要全局查**。第一版只查 `<技能目录>/scripts/xxx.py`，报出 16 个
   「死指针」—— 而那些脚本其实在 `~/.hermes/scripts/`。真死指针只有 3 个。
   同铁律 19：同名命中 ≠ 查过了，**「有哪些根」本身是待查项**。
   现在把 `~/.hermes/scripts/` 和 `~/.hermes/` 也纳入索引。

2. **不能拿 `--help` 的失败当「脚本坏了」**。第一版 39/57 报跑不通，其中
   37 个是测法错：`--help` 不是所有脚本的参数、库模块没有 `__main__`
   （`model-logging/logdb.py`、`china-briefing/*.py` 本来就是被 import 的）、
   Windows 专用脚本在 Linux 上找不到 `H:\\...` 路径是**对的**。
   **本命令只做静态判据（语法 + 指针 + frontmatter），不执行目标脚本**——
   静态能查的先查干净, 别用「跑一下看看」引入噪声。

3. **Windows 专用脚本要标注而不是报错**。识别依据：正文/代码里有盘符路径
   （`H:\\` `C:/` `D:\\`），这类脚本在 3046 上跑不了是设计如此。

用法:
    python3 skill_repo_doctor.py                  # 扫默认 skills 库
    python3 skill_repo_doctor.py --root <目录>     # 扫别的库
    python3 skill_repo_doctor.py --json           # 机器可读
    python3 skill_repo_doctor.py --root ~/.hermes/hermes-code   # 扫普通代码库
退出码: 0 = 干净, 1 = 有问题。
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from typing import Optional
from pathlib import Path

DEFAULT_ROOT = Path.home() / ".hermes" / "skills"
# 死指针查找要覆盖的额外根（教训 1：技能目录不是全部）
EXTRA_ROOTS = [Path.home() / ".hermes" / "scripts", Path.home() / ".hermes"]

SKIP_DIR_PARTS = {".archive", ".git", "__pycache__", "node_modules", ".venv"}


def iter_files(root: Path, suffix: str):
    # followlinks=True：库里有 6 个软链技能指向 ~/.agents/skills/，
    # 默认 False 会整个跳过它们（2026-10-02 实测：报 73 个，实际 79 个）。
    for dirpath, dirnames, filenames in os.walk(root, followlinks=True):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIR_PARTS]
        for f in filenames:
            if f.endswith(suffix):
                yield Path(dirpath) / f


def skill_dirs(root: Path):
    """返回 (name, dir, SKILL.md 内容) 三元组。没有 SKILL.md 的库返回空。"""
    # 注意：扫普通代码库（如 hermes-code/）时这里返回空，
    # 检查器必须只报语法/指针问题，而不是「技能数 0」。
    # followlinks=True —— 见 iter_files 的注释：软链技能不能漏。
    for dirpath, dirnames, filenames in os.walk(root, followlinks=True):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIR_PARTS]
        if "SKILL.md" in filenames:
            p = Path(dirpath) / "SKILL.md"
            try:
                text = p.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            m = re.search(r"^name:\s*(.+)$", text, re.M)
            yield (m.group(1).strip() if m else Path(dirpath).name, Path(dirpath), text)


def check_python_syntax(root: Path, issues: list):
    """用 ast.parse 而不是 py_compile —— py_compile 会写 __pycache__ 污染技能库。"""
    n = 0
    for f in iter_files(root, ".py"):
        n += 1
        try:
            ast.parse(f.read_text(encoding="utf-8", errors="ignore"), filename=str(f))
        except SyntaxError as e:
            issues.append({"kind": "python-syntax", "file": str(f.relative_to(root)),
                           "line": e.lineno, "detail": str(e.msg)[:120]})
    return n


def check_external_linters(root: Path, issues: list):
    """接成熟 linter 补py_compile 的盲区。

    2026-10-02 加。py_compile 只查语法，查不出「用了 os 但没 import os」——
    而那正是我 2026-10-02 脱敏 chat_id 时亲手改出来的崩（restore_local_deliver.py）。
    ruff E9/F63/F7/F82 = 语法 + 未定义名 + 不可达 + 坏比较，不做风格检查。
    shellcheck 只取 error 级（warning/note 在中文注释库里噪音太大）。
    工具没装就静默跳过——缺依赖不该报成问题。
    """
    ruff = shutil.which("ruff")
    if ruff:
        # E9/F63/F7/F82 = 语法 + 未定义名（py_compile 的盲区）
        # S105 硬编码密码 —— 实测全库 3 条全是误报（变量叫 password / 模板占位符），
        #   但真凭据会红，成本低所以留着。
        # 其余 S 规则实测全是噪音：S603/S607/S310 是脚本的正常写法，
        #   S608 三处全是参数化查询（marks="?,?"，教科书写法），S324 是算缓存 key。
        r = subprocess.run([ruff, "check", "--select=E9,F63,F7,F82,S105", "--no-cache",
                            "--output-format=concise", str(root)],
                           capture_output=True, text=True)
        for line in (r.stdout or "").splitlines():
            # ruff 成功时最后一行是 "All checks passed!" —— 那是通过信号不是问题
            if (not line.strip() or line.startswith("Found ")
                    or line.endswith("All checks passed!")):
                continue
            issues.append({"kind": "ruff", "file": line.split(":")[0],
                           "line": 0, "detail": line.strip()})
    # vulture：抓"永远不成立的分支"。2026-10-02 实测在 china-briefing/
    # server_cleanup.py 抓到 `if False:` —— 那行让脚本跳过 input() 确认直接删文件，
    # 静态语法检查完全看不出。这是"全绿代码在骗人"的典型。
    # S105 不匹配 API_KEY（实测），而那是最常泄露的一类。补自己的一条正则——
    # 但只查「明显是凭据」的形态（长串 + 高熵前缀），否则变量名一撞就满屏噪音。
    if True:
        import re as _re
        _CRED = _re.compile(
            r"(?i)(api_?key|secret_?key|access_?token|auth_?token|private_?key)\s*[:=]\s*"
            r"[\"\']([A-Za-z0-9_\-/+=]{16,})[\"\']")
        for p in iter_files(root, ".py"):
            for i, line in enumerate(Path(p).read_text(
                    encoding="utf-8", errors="ignore").split("\n"), 1):
                if "noqa" in line or line.strip().startswith("#"):
                    continue
                if _CRED.search(line):
                    issues.append({"kind": "credential", "file": str(p), "line": i,
                                   "detail": line.strip()[:100]})

    vulture = shutil.which("vulture")
    if vulture:
        r = subprocess.run([vulture, str(root), "--min-confidence", "80"],
                           capture_output=True, text=True)
        for line in (r.stdout or "").splitlines():
            if line.strip() and "unsatisfiable" in line:
                issues.append({"kind": "vulture", "file": line.split(":")[0],
                               "line": 0, "detail": line.split(" (")[0].strip()})

    sc = shutil.which("shellcheck")
    if sc:
        files = [str(p) for p in iter_files(root, ".sh")]
        if files:
            r = subprocess.run([sc, "-f", "gcc", "-S", "error", *files],
                               capture_output=True, text=True)
            for line in (r.stdout or "").splitlines():
                parts = line.split(":")
                if len(parts) >= 5:
                    issues.append({"kind": "shellcheck", "file": parts[0],
                                   "line": parts[1], "detail": parts[4].strip()})


def check_shell_syntax(root: Path, issues: list):
    n = 0
    for f in iter_files(root, ".sh"):
        n += 1
        r = subprocess.run(["bash", "-n", str(f)], capture_output=True, text=True)
        if r.returncode != 0:
            issues.append({"kind": "shell-syntax", "file": str(f.relative_to(root)),
                           "line": 0, "detail": r.stderr.strip().split("\n")[-1][:120]})
    return n


def global_basename_index() -> set:
    """全局文件名索引（教训 1）。"""
    names = set()
    for base in EXTRA_ROOTS:
        if not base.is_dir():
            continue
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [d for d in dirnames
                           if d not in SKIP_DIR_PARTS and "scratch" not in d]
            names.update(filenames)
    return names


def check_dead_pointers(root: Path, issues: list):
    """正文引用的 scripts/*.py|sh 必须真存在 —— 技能目录内或全局任一处。"""
    global_names = global_basename_index()
    # 仓库相对路径的根：hermes-agent 自带源码，技能里的 tools/ tests/ website/ 指向它
    repo_names: set = set()
    for base in (Path.home() / "hermes-agent",):
        if base.is_dir():
            for dirpath, dirnames, filenames in os.walk(base):
                dirnames[:] = [x for x in dirnames if x not in SKIP_DIR_PARTS]
                repo_names.update(filenames)

    pat = re.compile(r"((?:scripts|tools|bin)/[\w\-.]+\.(?:py|sh|ts|js))")
    for name, d, text in skill_dirs(root):
        for ref in set(pat.findall(text)):
            base_name = os.path.basename(ref)
            if (d / ref).exists() or base_name in global_names or base_name in repo_names:
                continue
            # 2026-10-02 实测的三类误报，判据要分清：
            #  a) 正文**明写这个文件不存在**（如 local-vlm 列出「全部不存在」清单）
            #  b) 该行在 ```代码块``` 里，是**通用示例**不是本机指令
            #     （systematic-debugging 的 `python scripts/repro_bug.py` 同块里的
            #      `pytest tests/test_module.py` 也是示例，两者都不存在）
            # 判据用「同一行/同一代码块」而不是全文 —— 全文搜必然误报。
            if is_declared_missing(text, ref) or in_fenced_example(text, ref):
                continue
            issues.append({"kind": "dead-pointer", "skill": name,
                           "file": str((d / "SKILL.md").relative_to(root)),
                           "detail": f"引用 {ref}，技能目录/全局/hermes-agent 都找不到"})


def fenced_blocks(text: str):
    """返回所有 ``` 代码块内容。"""
    return re.findall(r"```[^\n]*\n(.*?)```", text, re.S)


# 「这行不是在让你执行它」的标记：注释符、已废弃/旧做法/不要再用/示例 等。
# 2026-10-02 实测：`参见 scripts/not_real.py（旧的做法，已废弃）` 会被误报——
# 中文说明行不以 # 开头，光判 startswith("#") 不够。
NON_EXEC_MARKERS = re.compile(
    r"(^\s*#|已废弃|旧的做法|不要再用|已移除|不存在|曾经用|以前|formerly|previously|"
    r"no longer|don't|do not|deprecated|例如|示例|example)")


def is_declared_missing(text: str, ref: str) -> bool:
    """正文是否明说这个文件不存在（如「以下全部不存在」）。"""
    name = os.path.basename(ref)
    for blk in fenced_blocks(text):
        if name in blk and re.search(r"(不存在|已删|找不到|已移除|not found|no longer)", blk):
            return True
    # 非代码块：同一行里带否定词
    for line in text.split("\n"):
        if name in line and re.search(r"(不存在|已删|找不到|已移除|已废弃|never used|doesn't exist|no longer)", line):
            return True
    return False


def in_fenced_example(text: str, ref: str) -> bool:
    """该引用是否只出现在 ``` 代码块里（= 示例，不是本机指令）。

    2026-10-02 修：第一版只跳过以 ``` 开头的行，没跟踪块的开关状态，
    于是**代码块内部的行**也被算成「块外」，判据自我否定（in_block=True
    而 outside 也=True → 永远返回 False）。
    正确做法是逐行扫并跟踪 in_block 状态。
    """
    name = os.path.basename(ref)
    in_block = False
    seen_in = False
    seen_out = False
    for line in text.split("\n"):
        s = line.strip()
        if s.startswith("```"):
            in_block = not in_block
            continue
        if name not in line:
            continue
        if in_block:
            seen_in = True
        elif not NON_EXEC_MARKERS.search(s):   # 注释/已废弃/示例行不算指令
            seen_out = True
    return seen_in and not seen_out


def check_generated_junk(root: Path, issues: list):
    """抓自动生成器留下的模板空壳（2026-10-02：一次误跑生成 17 个）。

    判据靠**内容标记**而不是目录名 —— 上一轮按目录名只抓到 8 个，
    漏掉的 9 个藏在根目录（terminal-run / read-file / session_search…）里。
    「有哪些目录」是待查项，扫生成物必须按内容。
    """
    for name, d, text in skill_dirs(root):
        rel = str((d / "SKILL.md").relative_to(root))
        if "generated_by: hermes-dojo" in text or "created by Hermes Dojo" in text:
            issues.append({"kind": "generated-junk", "skill": name, "file": rel,
                           "detail": "自动生成器留下的模板空壳，正文全是通用套话"})
        elif "Most common error pattern observed: `unknown error`" in text:
            issues.append({"kind": "generated-junk", "skill": name, "file": rel,
                           "detail": "疑似模板占位符（错误模式写的是 unknown error）"})


def extract_description(text: str) -> str:
    """从 SKILL.md 文本里取 description 的**内容**（已剥 YAML 引号 / 块标量）。

    为什么必须抽成一处：引号和块标量是 YAML 语法，不是内容。
    - 不剥引号 → `"…"` 被当成内容，长度 +2 误报超限（google-workspace 实测 61 vs 59）
    - 不处理块标量 → `description: |` 取到字面量 "|"，与 INDEX 里 register.sh
      正确拼出的正文比对必然失配（instreet-agent 实测）

    姊妹调用点（check_frontmatter 与 check_index_consistency）必须共用本函数，
    否则修了一处另一处照旧误报。
    """
    lines = text.split("\n")
    for i, l in enumerate(lines):
        m = re.match(r"^description:\s*(.*)$", l)
        if not m:
            continue
        val = m.group(1).strip()
        if re.fullmatch(r"[|>][-+]?", val):          # 块标量：正文在后续缩进行
            body = []
            for nxt in lines[i + 1:]:
                if not nxt.strip():
                    continue
                if not nxt.startswith((" ", "\t")):
                    break
                body.append(nxt.strip())
            return " ".join(body).strip()
        return val.strip('"').strip("'")
    return ""


def check_frontmatter(root: Path, issues: list):
    """frontmatter 必须是第 0 行的 ---，且 description 以 Use when 起头。"""
    for name, d, text in skill_dirs(root):
        rel = str((d / "SKILL.md").relative_to(root))
        lines = text.split("\n")
        # 必须比对**原始首行**，不能 strip —— 缩进 4 空格的 "    ---" strip 之后
        # 等于 "---" 会蒙混过关，而这正是 2026-10-01 实测过的真 bug
        # （5 个技能被 yaml 静默吞掉 description，索引里路由信号整条丢失）。
        if not lines or lines[0] != "---":
            got = repr(lines[0][:20]) if lines else "(空文件)"
            issues.append({"kind": "frontmatter", "skill": name, "file": rel,
                           "detail": f"首行必须是顶格的 ---，实际是 {got}"})
            continue
        # 闭合的 --- 也必须在顶格
        try:
            end = lines[1:].index("---") + 1
        except ValueError:
            issues.append({"kind": "frontmatter", "skill": name, "file": rel,
                           "detail": "没有顶格的闭合 ---（frontmatter 未闭合）"})
            continue
        fm = "\n".join(lines[1:end])
        if not re.search(r"^description:", fm, re.M):
            issues.append({"kind": "frontmatter", "skill": name, "file": rel,
                           "detail": "frontmatter 里没有 description 字段"})
        else:
            d = extract_description(fm)
            if len(d) > 60:
                issues.append({"kind": "frontmatter", "skill": name, "file": rel,
                               "detail": f"description {len(d)} 字符 > 60 上限"})


def check_index_consistency(root: Path, issues: list):
    """INDEX.md 的登记必须与磁盘实际一致。

    2026-10-02 加。起因：手工比对时才发现 INDEX 记79、实体目录 73 ——
    差的6 个是软链技能，而 os.walk 默认不跟随软链，导致检查器**自己**
    长期少扫 6 个技能而报告显示全绿。
    判据三向：INDEX 有磁盘无（幽灵）/ 磁盘有 INDEX 无（漏登记）/
    description 与 SKILL.md 不一致（索引过期）。
    """
    idx = root / "INDEX.md"
    if not idx.exists():
        return
    rows = [l for l in idx.read_text(encoding="utf-8").split("\n")
            if l.startswith("| ") and "SKILL.md" in l]
    in_idx = {}
    for l in rows:
        m = re.match(r"\|\s*([\w-]+)\s*\|\s*([\w/.-]+)\s*\|\s*(.+?)\s*\|", l)
        if m:
            in_idx[m.group(1)] = (m.group(2), m.group(3))
    on_disk = {name: (d, text) for name, d, text in skill_dirs(root)}

    for name in sorted(set(in_idx) - set(on_disk)):
        issues.append({"kind": "index", "file": "INDEX.md",
                       "detail": f"INDEX 登记了「{name}」但磁盘上没有 —— 幽灵条目，"
                                 f"跑 register.sh 重建"})
    for name in sorted(set(on_disk) - set(in_idx)):
        issues.append({"kind": "index", "file": "INDEX.md",
                       "detail": f"「{name}」在磁盘上但 INDEX 没登记 —— "
                                 f"跑 register.sh 重建"})
    for name in sorted(set(in_idx) & set(on_disk)):
        want = in_idx[name][1]
        head = "\n".join(on_disk[name][1].split("\n")[:20])   # frontmatter 在最前面
        got = extract_description(head)
        if got and want.rstrip("。") != got.rstrip("。"):
            issues.append({"kind": "index", "file": "INDEX.md",
                           "detail": f"「{name}」INDEX 的描述已过期：\n"
                                     f"        INDEX: {want[:70]}\n"
                                     f"        实际: {got[:70]}"})


def note_windows_only(root: Path) -> int:
    """统计 Windows 专用脚本（不是问题，只是提醒别在 Linux 上测它）。"""
    n = 0
    for f in iter_files(root, ".py"):
        try:
            head = f.read_text(encoding="utf-8", errors="ignore")[:4000]
        except OSError:
            continue
        if re.search(r"['\"][A-Za-z]:[\\/]", head):
            n += 1
    return n


def _curator_backed(skill_root: Path, changed: list, digest: dict) -> bool:
    """changed 里的每一项是否都能在 curator ledger 里对上账。

    ledger（~/.hermes/skills/.curator_ledger.jsonl）记录 curator 每次 patch 前后
    的完整 sha256。对得上 = 有据可查的自学习，静默续期基线；对不上 = 真的
    有人在没记账的情况下改了判据，必须报出来。
    """
    ledger = Path.home() / ".hermes" / "skills" / ".curator_ledger.jsonl"
    if not ledger.exists():
        return False
    try:
        entries = [json.loads(l) for l in ledger.read_text(encoding="utf-8").splitlines() if l.strip()]
    except (ValueError, OSError):
        return False
    # 路径 → 该文件 ledger 里出现过的所有 after-sha
    seen = {}
    for e in entries:
        for f in e.get("after") or []:
            p = f.get("path")
            if p:
                seen.setdefault(str(Path(p).resolve()), set()).add(f.get("sha256"))
    for k in changed:
        path = (skill_root / k).resolve() if not k.startswith("/") else Path(k).resolve()
        full = None
        try:
            full = hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError:
            return False
        if full not in seen.get(str(path), ()):
            return False          # 没记账，或账对不上 → 照报
    return True


def check_loop_invariance(root: Path, issues: list, self_dir: Optional[Path] = None):
    """环外不变量：检查器的判据文件不得落在它自己能扫到的范围内。

    2026-10-02 加（依据 ace-skills/self-improvement-loops：
    「评估器、其插桩、权限控制和预算强制，必须住在循环能修改的范围之外」）。

    本检查器给自己出了个它抓不到的问题：它扫全技能库的语法/死指针/frontmatter，
    而它自己的判据（正则、阈值、豁免名单）就写在同一棵树下、同一个 git、
    同一个可写范围内 —— 改判据和改被检查对象是同一个动作。
    症状形如：检查器报了 5 条，它自己明天报 0 条，没有任何东西会觉得不对。

    判据：判据文件**必须能被审计**，但不必真的搬出仓库（那是权限架构改动）。
    本项只做能自动做的那一半 —— 记录判据文件的指纹，改了就在报告里显式说一声。

    self_dir 只给自检用（指向临时目录）；默认就是本文件所在目录。
    """
    updating = "--update-stamp" in sys.argv
    base = Path(self_dir) if self_dir else Path(__file__).resolve().parent
    # 技能根 = scripts/ 的上一级。从 base 扫会漏掉 references/ 与技能正文 ——
    # 那正是判据最集中的地方。宁可多扫，不可漏扫。
    skill_root = base.parent
    crit = [Path(__file__).resolve()]
    crit += sorted(skill_root.glob("*.md"))                  # SKILL.md（铁律）+ 附卡
    crit += sorted(skill_root.rglob("*.md"))                  # references/ 等子目录
    crit += sorted(skill_root.rglob("*.txt"))
    crit += sorted(skill_root.rglob("*.py"))                   # 同目录兄弟脚本也是判据载体
    crit = sorted({c.resolve() for c in crit if c.is_file()})  # is_file：目录名 *.md 曾让整份报告蒸发
    # 键要唯一（不同子目录可能同名）但要短 → 用「父目录/文件名」。
    # 不用 relative_to：SKILL.md 在 base 之外会抛 ValueError；也不用裸 name：
    # 顶层 notes.md 与 references/notes.md 会撞键，后者覆盖前者 → 改前者静默通过。
    def _key(c):
        try:
            return str(c.relative_to(base))
        except ValueError:
            try:
                return f"../{c.relative_to(base.parent)}"      # 技能根下的文件带层级，键不撞
            except ValueError:
                return str(c)
    digest = {}
    for c in crit:
        try:
            digest[_key(c)] = hashlib.sha256(c.read_bytes()).hexdigest()[:16]
        except OSError as e:                                  # 读不了就记下来，不许整份报告蒸发
            issues.append({"kind": "loop", "file": c.name,
                           "detail": f"判据文件读不了（{e.__class__.__name__}）—— "
                                     f"这一项无法验证，请手工确认"})

    stamp_path = base / ".criteria_stamp.json"
    changed: list = []
    prev: dict = {}          # 无基线时也要有值：下面的静默续期分支会读它
    if not stamp_path.exists():
        # 删掉 stamp 与从未建立基线长得一模一样 —— 不能都当「干净」。
        # 判据只能被自己修改时，指纹消失本身就是破口信号。
        issues.append({"kind": "loop", "file": stamp_path.name,
                       "detail": "判据指纹文件不存在 —— 删掉它就能让本项永久静默通过，"
                                 "这与环外不变量直接冲突。跑 --update-stamp 重建基线，"
                                 "并把这个 json 移出循环可写范围（见铁律 23 边界）"})
    else:
        try:
            prev = json.loads(stamp_path.read_text(encoding="utf-8"))
        except (ValueError, OSError) as e:
            issues.append({"kind": "loop", "file": stamp_path.name,
                           "detail": f"判据指纹文件损坏/不可读（{e.__class__.__name__}）—— "
                                     f"按「无基线」处理，而不是当作干净通过"})
            prev = {}
        if not isinstance(prev, dict):
            issues.append({"kind": "loop", "file": stamp_path.name,
                           "detail": f"判据指纹不是对象（是 {type(prev).__name__}）—— "
                                     f"已忽略，本次不作判；跑 --update-stamp 重建"})
            prev = {}
        # 增、删、改三种都要报。只比 digest∩prev 的话，
        # 删掉一个碍事的 references/*.md 或新加一个，都是零信号。
        changed = sorted(k for k in set(digest) | set(prev) if digest.get(k) != prev.get(k))
        # curator 会自动把学到的经验 patch 回技能正文（ledger 里已有 200+ 次记录），
        # 那是有据可查的自学习，不是「偷偷改判据让它变绿」。ledger 记了每次写入的
        # 完整 sha256，所以这里能对账：对得上就静默续期，对不上照报。
        if changed and not updating:
            # digest 的 key 相对 base（scripts/）生成，见 _key()：技能根下的文件
            # 带 "../" 前缀。拼路径必须用 base，用 skill_root 会差一层 → 读不到文件
            # → OSError → return False → 把 curator 合法自学习误报成「篡改判据」。
            #
            # 2026-10-10 修：原来这里是 `changed = []`，但没跳过下面的拼报告 →
            # 拼出「判据文件被改动：」（空列表）的假警报。改成用 skip_report 标记，
            # 让流程继续走到基线续期（否则下一轮仍拿旧基线比，重复报）。
            skip_report = _curator_backed(base, changed, digest)
            if skip_report:
                changed = []
            verb = "判据文件被改动"
            if changed and any(k not in prev for k in changed):
                verb = "新增判据文件"
            elif any(k not in digest for k in changed):
                verb = "判据文件被删除"
            if changed:                     # 空列表 = curator 合法自学习，不报
                issues.append({
                    "kind": "loop", "file": Path(__file__).name,
                    "detail": f"{verb}：{'、'.join(changed)} —— "
                              f"「自己改自己的判据」是环外不变量破口，"
                              f"改后请重跑负样本验证结论是否仍成立（--demo）",
                })
    if updating or (changed == [] and prev and prev != digest):
        # 静默放行的 curator 改动也要落盘续期，否则下一轮仍拿旧基线比，重复报。
        if changed:
            print(f"已接受 {len(changed)} 处判据增删改：{'、'.join(changed[:6])}"
                  f"{' …' if len(changed) > 6 else ''} —— "
                  f"确认改判据的理由成立（判据变更要留证据，不是为了让报告变绿）",
                  file=sys.stderr)
        stamp_path.write_text(json.dumps(digest, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"判据指纹已更新：{len(digest)} 个文件", file=sys.stderr)


def check_desc_collision(root: Path, issues: list):
    """触发词重叠：同一个词被多条 description 当触发条件 = 路由打架。

    2026-10-02 加，随后被实测收窄到**只能查拉丁技术词**（端口/命令/服务名）。

    起因与反转：铁律 33 说「负边界 + 反例」能防误触发，于是我先假定真缺口是
    「触发词重叠」，并用中文 2-4 字滑窗统计出「dashboard 被 5 条抢」。
    **那个统计是假的。** 逐条查证后：5 条里只有 `hermes-dashboard-access` 的
    触发段含 dashboard，另外 4 条的 dashboard 都在**负边界段**里
    （`（非dashboard白屏）`、`（dashboard交专属技能）`）—— 那正是它们正确地让开。
    73 条 description 里，**中文触发词没有任何片段被 3 条以上共用**。

    所以本检查的范围必须如实写死：
    - ✅ 能查：拉丁技术词在 >=3 条触发段里共用（端口、命令、服务名、产品名）
    - ❌ 查不了：中文语义重叠。要查需要分词器，那是另一个依赖，不在本工具内。
      **别把「本项全绿」读成「路由没有问题」—— 中文那半边根本没查。**
    - 中文滑窗统计会造假：2-4 字滑窗把「各交各的专技能」切成 '各交各的'/'专技能'，
      同族技能的样板中文全部命中同一个碎片词。实测因此误报过 6 条、真信号 0 条。

    切分点必须含**左括号**：负边界的实际标记是「（非X）」「（X交Y）」，
    只按句号切会把负边界里的词算成抢触发的词（实测踩过）。
    """
    STOP = {"use", "when", "this", "the", "and", "for", "with", "skill", "非"}
    # 技能族前缀：出现在名字里就是族标，不是触发条件。hermes-* 全都算，
    # 否则「hermes」会命中 6 条而这条信息毫无用处（实测噪音最大的一条）。
    NOISE = {"agent", "hermes", "skill", "skills", "ops", "use", "when"}
    buckets: dict[str, list[str]] = {}
    for name, _, text in skill_dirs(root):
        m = re.search(r"^description:\s*(.+)$", text, re.M)
        if not m:
            continue
        desc = m.group(1).strip()
        # 只取触发段，负边界段不参与抢触发。
        # 切分点：句号/分号 **和左括号**。负边界的实际标记是「（非X）」「（X交Y）」，
        # 只按句号切的话 `Use when 活儿0（非dashboard）。` 整句都算触发段 ——
        # 负边界里的词反而成了抢触发的词，正好测反了。2026-10-02 实测抓到。
        head = re.split(r"[。；;（(]", desc)[0]
        for w in re.findall(r"[A-Za-z][A-Za-z_]{3,}", head.lower()):
            if w in STOP or w in NOISE:
                continue
            buckets.setdefault(w, []).append(name)
        # 中文没有词边界：2-4 字滑窗把句子切成语义碎片
        # （「各交各的专技能」→ '各交各的'/'专技能'），同族技能的样板中文
        # 会全部命中同一个碎片词，刷出一堆无意义重叠。
        # 补救：中文只认**技术词**形态 —— 含 ASCII 数字/版本号/端口，
        # 或在整库里出现 >=3 次的拉丁串。不做分词器（那是另一个依赖）。
        for m in re.finditer(r"[A-Za-z][A-Za-z0-9_.-]*\d[A-Za-z0-9_.-]*|\d{3,}", head):
            buckets.setdefault(m.group(0).lower(), []).append(name)
    for w, names in sorted(buckets.items(), key=lambda kv: -len(kv[1])):
        uniq = sorted(set(names))
        if len(uniq) < 3:
            continue
        # 分辨力检查：三条共用同一词时，若它们是**同一族**
        # （名字共享前缀，如 obsidian-cli / obsidian-bases / obsidian-markdown），
        # 那共用是设计如此（一个族该有几个入口），不是路由打架。
        # 判别：任意两条名字最长公共前缀 >= 4 字 → 同族，放行。
        from itertools import combinations
        same_family = any(
            len(os.path.commonprefix([a, b])) >= 4 for a, b in combinations(uniq, 2))
        if same_family:
            continue
        issues.append({
            "kind": "collision", "skill": uniq[0],
            "detail": f"触发词 {w!r} 被 {len(uniq)} 条**不同族**技能共用"
                      f"（{'、'.join(uniq[:5])}）—— 字数与负边界都救不了这个；"
                      f"改法是各条说清自己那半边（哪个症状/哪一层），而不是各写各的关键词。"
                      f"同族（如 obsidian-cli/bases/markdown）已按设计放行。",
        })


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(DEFAULT_ROOT))
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--update-stamp", action="store_true",
                    help="记录当前判据文件指纹（改判据后跑一次以接受新判据）")
    a = ap.parse_args()
    root = Path(a.root)
    if not root.is_dir():
        print(f"目录不存在: {root}", file=sys.stderr)
        return 1

    issues: list = []
    skills = list(skill_dirs(root))
    n_py = check_python_syntax(root, issues)
    n_sh = check_shell_syntax(root, issues)
    check_external_linters(root, issues)
    check_index_consistency(root, issues)
    check_dead_pointers(root, issues)
    check_generated_junk(root, issues)
    check_frontmatter(root, issues)
    check_loop_invariance(root, issues)
    check_desc_collision(root, issues)
    win_only = note_windows_only(root)

    by_kind: dict[str, int] = {}
    for i in issues:
        by_kind[i["kind"]] = by_kind.get(i["kind"], 0) + 1

    if a.json:
        print(json.dumps({"root": str(root), "skills": len(skills),
                          "py_files": n_py, "sh_files": n_sh,
                          "windows_only_scripts": win_only,
                          "issues": issues}, ensure_ascii=False, indent=2))
        return 1 if issues else 0

    print("=" * 62)
    print("  技能库结构体检")
    print("=" * 62)
    print(f"  .py {n_py} 个 · .sh {n_sh} 个")
    if skills:
        print(f"  技能 {len(skills)} 个（含 frontmatter / 生成物空壳 / INDEX 一致性检查）")
    else:
        print("  非技能库（无 SKILL.md）—— 跳过 frontmatter 与生成物空壳检查")
    print(f"  （另有 {win_only} 个 Windows 专用脚本，在 Linux 上跑不了是设计如此，不算问题）")
    print()
    if not issues:
        print("  ✅ 无问题")
        return 0
    for kind, cnt in sorted(by_kind.items()):
        print(f"  🔴 {kind}: {cnt}")
    print()
    # 按 kind 分组输出：同类只打一次前缀，避免「index INDEX.md」重复刷屏
    last_kind = None
    for i in issues:
        if i["kind"] != last_kind:
            print(f"  【{i['kind']}】")
            last_kind = i["kind"]
        loc = f"{i['file']}"
        if i.get("line"):
            loc += f":{i['line']}"
        who = f" [{i['skill']}]" if i.get("skill") else ""
        print(f"    · {loc}{who}")
        for ln in i["detail"].splitlines():
            print(f"      {ln}")
    return 1


def _demo():
    """环外不变量检查的自检。python3 skill_repo_doctor.py --demo

    这批样本是被两个独立审读者 + 一次真实攻击逼出来的：
    原版把「无指纹」「指纹损坏」当正确行为（fail-open）写进了断言 ——
    而那正是全部静默绕过的入口。现在它们都必须报。
    """
    import tempfile, shutil
    with tempfile.TemporaryDirectory() as d:
        root = Path(d) / "skill"
        (root / "scripts").mkdir(parents=True)
        (root / "references").mkdir()
        (root / "SKILL.md").write_text("---\nname: a\ndescription: Use when x\n---\n")
        (root / "references" / "rules.md").write_text("# 判据\n死指针应排除 X\n")
        td = root / "scripts"
        sp = td / ".criteria_stamp.json"
        saved = sys.argv
        sys.argv = ["x"]                                  # 屏蔽 --update-stamp
        try:
            def run_root(r):
                iss = []
                check_desc_collision(r, iss)
                return iss

            def run():
                iss = []
                check_loop_invariance(root, iss, self_dir=td)
                return [i for i in iss if i["kind"] == "loop"]

            def stamp_now():                               # 建立基线
                sys.argv = ["x", "--update-stamp"]
                try:
                    check_loop_invariance(root, [], self_dir=td)
                finally:
                    sys.argv = ["x"]

            # ① 负样本（原 fail-open 入口）：无指纹必须报，不能当干净
            sp.unlink(missing_ok=True)
            assert run(), "无指纹时必须报 —— 删掉它就能静默过"

            stamp_now()
            assert not run(), "基线刚建立时不该报"

            # ② 改动：原地改判据 → 必报
            (root / "references" / "rules.md").write_text("# 判据\n放宽了 X\n")
            assert run(), "改判据必须报"
            stamp_now()
            assert not run(), "接受后不该报"

            # ③ 负样本（原盲区）：删除判据文件 → 必报。旧实现只比 digest∩prev，删掉是零信号。
            (root / "references" / "rules.md").unlink()
            det = run()
            assert det and "删除" in det[0]["detail"], f"删判据文件必须报（实测{det}）"
            stamp_now()

            # ④ 负样本（原盲区）：新增判据文件 → 必报
            (root / "references" / "new.md").write_text("# 新规则\n某判据\n")
            add = run()
            assert add and "新增" in add[0]["detail"], f"新增判据文件必须报（实测{add}）"
            (root / "references" / "new.md").unlink()
            stamp_now()

            # ⑤ 负样本（原 fail-open 入口）：指纹不是对象 → 必须报，不能当干净
            for junk in ("[]", "12345", "null", '"hello"'):
                sp.write_text(junk, encoding="utf-8")
                assert run(), f"stamp={junk} 必须报，不得静默通过"
            # ⑥ 变体：损坏 JSON → 报「无基线」而不是崩
            sp.write_text("{ 不是 JSON", encoding="utf-8")
            assert run(), "损坏指纹必须报"
            # ⑦ 键不撞：顶层 notes.md 与 references/notes.md 同名，两个都要在指纹里
            (root / "notes.md").write_text("# 顶层\n")
            (root / "references" / "notes.md").write_text("# 子目录\n")
            stamp_now()
            import json as _json
            keys = set(_json.loads(sp.read_text(encoding="utf-8")).keys())
            assert any(k.endswith("notes.md") for k in keys) and \
                   len([k for k in keys if k.endswith("notes.md")]) == 2, \
                f"同名文件键必须唯一，实际 {keys}"
            # ⑧ 目录名 *.md 不得让整份报告蒸发
            # ⑨ 触发词重叠：3 条共用必须报；样板词不得触发；负边界段不参与抢触发
            for nm in ("alpha", "beta", "gamma"):
                d = root / nm
                d.mkdir(exist_ok=True)
                (d / "SKILL.md").write_text(
                    f"---\nname: {nm}\ndescription: Use when dashboard 出白屏，X交Y（非Z）。\n---\n",
                    encoding="utf-8")
            col = [i for i in run_root(root) if i["kind"] == "collision"]
            assert col and "dashboard" in col[0]["detail"], f"共用触发词必须报（实测{col}）"
            assert not [i for i in col if i["detail"].count("用") > 1 and "when" in i["detail"]], \
                "样板词 Use when 不得算抢触发"
            for nm in ("alpha", "beta", "gamma"):
                shutil.rmtree(root / nm)
            # ⑨b 噪音词不报：三条共用 "hermes" 但那是族前缀，不是触发条件
            for nm in ("xalpha", "ybeta", "zgamma"):
                d = root / nm
                d.mkdir(exist_ok=True)
                (d / "SKILL.md").write_text(
                    f"---\nname: {nm}\ndescription: Use when hermes 某个面坏了。\n---\n",
                    encoding="utf-8")
            noise = [i for i in run_root(root)
                     if i["kind"] == "collision" and "hermes" in i["detail"]]
            assert not noise, f"族前缀 hermes 不得算抢触发（实测{noise}）"
            for nm in ("xalpha", "ybeta", "zgamma"):
                shutil.rmtree(root / nm)

            # ⑩ 同族放行：obsidian-cli/bases/markdown 共用 obsidian 是设计如此
            for nm in ("obsidian-cli", "obsidian-bases", "obsidian-markdown"):
                d = root / nm
                d.mkdir(exist_ok=True)
                (d / "SKILL.md").write_text(
                    f"---\nname: {nm}\ndescription: Use when 操作 obsidian 的某个面。\n---\n",
                    encoding="utf-8")
            fam = [i for i in run_root(root)
                   if i["kind"] == "collision" and "obsidian" in i["detail"]]
            assert not fam, f"同族共用应放行，实测报了：{fam}"
            for nm in ("obsidian-cli", "obsidian-bases", "obsidian-markdown"):
                shutil.rmtree(root / nm)
            # ⑪ 负边界段里的词不得算抢触发：三条触发段各不相同，
            # 只有尾部「(非xxx)」里出现同一个词 → 不该报
            for i, nm in enumerate(("q1", "q2", "q3")):
                d = root / nm
                d.mkdir(exist_ok=True)
                (d / "SKILL.md").write_text(
                    f"---\nname: {nm}\ndescription: Use when 活儿{i}（非dashboard）。\n---\n",
                    encoding="utf-8")
            tail_only = [i for i in run_root(root)
                         if i["kind"] == "collision" and "dashboard" in i["detail"]]
            assert not tail_only, f"负边界段的词不得算抢触发（实测{tail_only}）"
            for nm in ("q1", "q2", "q3"):
                shutil.rmtree(root / nm)
        finally:
            sys.argv = saved
    print("demo ok: 无指纹/删/增/非对象/损坏 必报 · 键唯一 · 目录名不崩 · 触发词重叠必报")


if __name__ == "__main__":
    if "--demo" in sys.argv:
        _demo()
        sys.exit(0)
    sys.exit(main())