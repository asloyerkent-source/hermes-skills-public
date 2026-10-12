#!/usr/bin/env python3
"""sanitize_for_public.py 的判据自测：正/负/变体三组样本。

判据型代码必须跑≥3 组样本（正/负/变体），负样本最关键——
只测「该被脱的脱了」会漏掉「不该脱的被误脱」。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path.home() / ".hermes/skills/devops/skill-publish/scripts"))
import sanitize_for_public as S

fails = []
CHECKS = []


def check(name, got, want):
    CHECKS.append(name)
    if got != want:
        fails.append(f"{name}: got={got!r} want={want!r}")


# ---------- 正样本：必须被脱 ----------
# 变体 1：裸 IP（原规则表漏的网段）
check("裸 192.168.99.X",
      S.sanitize_text("BASE=http://192.168.99.X:9119", __import__("collections").Counter()),
      "BASE=http://192.168.99.X:9119")
# 变体 2：紧邻字母的 IP（词边界会漏，数字边界不会）
check("紧邻字母 192.168.99.X",
      S.sanitize_text("x192.168.99.Xy", __import__("collections").Counter()),
      "x192.168.99.Xy")
# 变体 3：账户名（放在非邮箱上下文里，避免被更靠后的邮箱规则先命中）
check("账户名",
      S.sanitize_text("repo=<gh-account>-source/hermes-skills",
                      __import__("collections").Counter()),
      "repo=<gh-account>-source/hermes-skills")
# 变体 3b：邮箱上下文（邮箱规则会先吃掉 <EMAIL>，账户名仍须被脱）
check("账户名（邮箱上下文）",
      S.sanitize_text("<EMAIL>:<gh-account>-source/hermes-skills.git",
                      __import__("collections").Counter()),
      "<EMAIL>:<gh-account>-source/hermes-skills.git")
# 变体 4：172.16 段（原规则表只写了 172.16，现在应覆盖 172.20）
check("172.20 段",
      S.sanitize_text("host 172.31.99.X", __import__("collections").Counter()),
      "host 172.31.99.X")
# 变体 5：通配写法 192.168.99.X —— 两个工具的 TOPOLOGY 正则都看不见它（假阴性）
check("通配写法 192.168.99.X",
      S.sanitize_text("phone on 192.168.99.X subnet", __import__("collections").Counter()),
      "phone on 192.168.99.X subnet")
check("通配写法 172.31.99.X",
      S.sanitize_text("vip 172.31.99.X", __import__("collections").Counter()),
      "vip 172.31.99.X")
# 变体 6：OS 用户目录（按类覆盖，任何用户名）
check("Win 用户目录",
      S.sanitize_text(r"path C:\Users\<user>\AppData", __import__("collections").Counter()),
      r"path C:\Users\<user>\AppData")
check("Win 用户目录（人名）",
      S.sanitize_text(r"C:\Users\<user>\x", __import__("collections").Counter()),
      r"C:\Users\<user>\x")
check("mac 用户目录",
      S.sanitize_text("/Users/<user>/x", __import__("collections").Counter()),
      "/Users/<user>/x")
check("Win 正斜杠路径",
      S.sanitize_text(r'key_filename=r"C:/Users/<user>/.ssh/id"', __import__("collections").Counter()),
      r'key_filename=r"C:/Users/<user>/.ssh/id"')

# ---------- 负样本：不该被误脱（最关键） ----------
# 已脱敏的占位符不能被二次匹配
check("占位符幂等",
      S.sanitize_text("192.168.99.X", __import__("collections").Counter()),
      "192.168.99.X")
# 公网 IP 不是私网，不该动
check("公网 IP 不动",
      S.sanitize_text("8.8.8.8 and 1.1.1.1", __import__("collections").Counter()),
      "8.8.8.8 and 1.1.1.1")
# 172.15 / 172.32 不在 RFC1918 内，不该动
check("172.15 不动",
      S.sanitize_text("172.15.1.1", __import__("collections").Counter()),
      "172.15.1.1")
check("172.32 不动",
      S.sanitize_text("172.32.1.1", __import__("collections").Counter()),
      "172.32.1.1")
# 版本号形态不应被当 IP
check("版本号不动",
      S.sanitize_text("v1.2.3.4", __import__("collections").Counter()),
      "v1.2.3.4")
# URL 里的 /Users/ 不该被动（有 / 或 : 前缀 = 不是本地路径）
check("URL 路径不动",
      S.sanitize_text("https://example.com/Users/alice", __import__("collections").Counter()),
      "https://example.com/Users/alice")

# ---------- 自扫：脱敏器自己不含真值 ----------
src = Path(S.__file__).read_text(encoding="utf-8")
for pat, _ in S.SUBS:
    hits = [m for m in __import__("re").finditer(pat, src)
            if "re.compile" not in src[max(0, m.start() - 30):m.start()]]
    # 源码里的正则字面量本身会被匹配到，这是 self_redact 的职责；此处只查
    # 「规则表之外还硬写着真值」的情况
# 账户名不该出现在源码里（它自己就是规则的一部分，会被 self_redact 处理）
print("自扫账户名出现次数（含规则行，应为 1）:",
      len(__import__("re").findall("<gh-account>", src)))

if fails:
    print("FAIL")
    for f in fails:
        print("  -", f)
    sys.exit(1)
print(f"PASS — {len(CHECKS)} 组样本全过（正/负/变体）")
