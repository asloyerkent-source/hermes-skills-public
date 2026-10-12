#!/usr/bin/env python3
"""
受控实测 v2：LLM 判官的长度偏差 + 位置偏差。

改进点（相对 v1）
----------------
1. 两种注水强度：
   - obvious：明显废话（免责声明、重复、口头禅）
   - subtle ：**专业但啰嗦**——事实相同，行文更铺陈（加背景段、复述机制、总结段）
     这才是真正的长度偏差测试：判官不能靠「一看就是废话」蒙对。
2. 每格重试 3 次 + 指数退避（kimi 账号 RPM 上限实测只有 3）。
3. 每轮超时 180s（LongCat 较慢）。

判读
----
- 长度偏差：注水版被选中比例。称职判官应显著 < 50%。
- 位置偏差：选「A」的比例。无偏差应接近 50%。
- **关键对照**：若 subtle 组注水版胜率明显高于 obvious 组，说明判官只在「废话明显」时
  才识别冗余——这本身就是长度偏差的间接证据。
"""
from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

# ── 材料 ────────────────────────────────────────────────────────────────
CONCISE = """看门狗失效的直接原因是判据层级错了。

它每一轮读的是 mihomo 控制口的 alive 字段——那是 TCP 握手延迟，只能证明「能连上」，
不能证明「流量真的过得去」。订阅服务器已经全挂、31 个节点真实请求全部返回 000 的时候，
这个字段依然是 true，所以它每轮都写 heal done: alive=9，日志一路绿灯。

修法是把判据换到同一层：真发一次 HTTPS 请求，看返回码，而不是看握手延迟。
另外它还有第二个问题——切节点时只比延迟，不看目标站是否可达，
所以会把流量切到一个能握手但过不去封锁的节点上。"""

# 明显注水：免责声明 + 重复 + 口头禅
PADDED_OBVIOUS = """关于看门狗为什么会失效这个问题，我认为需要从多个角度来进行一个比较系统的分析，
下面我会尽可能全面地展开说明，希望能够帮助理解这个问题的本质。

首先，我们要明确一点，看门狗机制在现代运维体系中扮演着非常重要的角色。
一个设计良好的看门狗，理论上应该能够及时发现问题、准确判断问题、并且采取合适的行动。
然而在实际的工程实践中，我们经常会遇到各种各样的复杂情况，这些情况往往会暴露出设计上的不足。

那么回到这个具体的案例。经过仔细的排查和分析，我们可以发现，这个看门狗失效的直接原因，
归根结底是判据的层级出现了错位。换句话说，它用来判断系统是否健康的那个指标，
和它真正想要保证的那个目标，并不在同一个层面上。

具体来说，它每一轮读取的是 mihomo 控制口提供的一个叫做 alive 的字段。
这个字段的含义是 TCP 握手是否成功，也就是说，它反映的只是「网络连接能不能建立起来」。
但是我们需要认识到，连接能建立，并不等于数据真的能够正常传输。
这是一个非常关键的区分，很多运维事故都源于没有区分好这两者。

在本次事件中，订阅服务器实际上已经完全不可用了，
31 个节点经过真实请求测试之后全部返回 000。
但即便在这种情况下，alive 这个字段依然显示为 true，
这就导致看门狗每一轮都记录下 heal done: alive=9 这样的日志，
从日志上看一切正常，实际上问题一直存在而没有被发现。

针对这个问题，修复的思路其实并不复杂，核心就是把判据提升到与目标相同的层级上：
不要再去参考握手延迟，而是真实地发起一次 HTTPS 请求，然后检查返回的状态码。
这样才能真正反映「流量是否通得过」。

除此之外，这个看门狗还存在第二个方面的问题，也值得一并说明。
它在进行节点切换的时候，仅仅是比较各个节点的延迟数值，
而没有去验证目标站点是否真的可以通过该节点访问。
这就带来一个后果：它有可能把流量切换到一个虽然能够完成握手、
但实际上无法穿透网络封锁的节点上去，从而使得问题看起来被解决了，实际却没有。"""

# 隐蔽注水：无废话，专业语气，但加背景段/复述/总结 —— 字数多一倍，信息量相同
PADDED_SUBTLE = """看门狗失效的直接原因是判据层级错了。

要理解这一点，需要先区分监控指标的两个层次。第一层是连通性，回答「连接能否建立」；
第二层是可用性，回答「数据能否真正通过」。大多数监控事故都发生在用第一层的指标
去担保第二层的目标。

这个看门狗正是这种情况。它每一轮读的是 mihomo 控制口的 alive 字段。
该字段的语义是 TCP 握手是否成功，属于第一层。它只能证明「能连上」，
不能证明「流量真的过得去」。当订阅服务器已经全挂、31 个节点真实请求全部返回 000 的时候，
这个字段依然是 true。于是它每轮都写 heal done: alive=9，日志一路绿灯，
而真实可用性其实已经是零。

修法是把这个判据换到与目标相同的层级：真发一次 HTTPS 请求，检查返回码，
用第二层的指标来担保第二层的目标，而不是继续参考握手延迟。

除了主判据的问题之外，这个看门狗还有第二个缺陷。
它在切换节点时只比较各节点的延迟数值，没有验证目标站点经由该节点是否真的可达。
延迟同样属于第一层的指标。因此它可能把流量切到一个能完成握手、
却过不去网络封锁的节点上——问题在日志上看起来被解决了，实际并没有解决。

把两处都修正之后，看门狗的判断才会与它要保证的目标处在同一层。"""

PROMPT_TMPL = """下面是一份技术问题回答的两个版本。请判断哪一个**质量更高**。

判断标准：信息是否准确、是否完整回答了问题、是否有冗余。

注意：两版包含的事实信息是相同的，区别只在于行文的长短与铺陈程度。

--- 版本 A ---
{A}

--- 版本 B ---
{B}

请只输出一行，格式严格为：
<选中的字母>|<一句话理由>
例如：A|理由"""

MODELS = [
    ("deepseek-flash", "deepseek",  "https://api.deepseek.com/v1",                       "deepseek-flash",  "DEEPSEEK_API_KEY"),
    ("qwen3.7-plus",   "dashscope", "https://dashscope.aliyuncs.com/compatible-mode/v1", "qwen3.7-plus",    "DASHSCOPE_API_KEY"),
    ("kimi-k2.7-code", "kimi",      "https://api.moonshot.cn/v1",                        "kimi-k2.7-code",  "KIMI_API_KEY"),
    ("LongCat-2.0",    "longcat",   "https://api.longcat.chat/openai",                   "LongCat-2.0",     "LONGCAT_API_KEY"),
]

ENV = Path.home() / ".hermes" / ".env"


def read_env() -> dict:
    out = {}
    for line in ENV.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def ask(base: str, key: str, model: str, prompt: str, tries: int = 3) -> str:
    body = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 600,
    }).encode()
    last = None
    for attempt in range(tries):
        req = urllib.request.Request(
            base.rstrip("/") + "/chat/completions", data=body,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            method="POST")
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                d = json.load(r)
            return (d["choices"][0]["message"].get("content") or "").strip()
        except Exception as exc:  # noqa: BLE001
            last = exc
            time.sleep(2 ** attempt * 3)
    raise last  # type: ignore[misc]


def parse_choice(text: str) -> str | None:
    m = re.search(r"\b([AB])\b", text)
    return m.group(1) if m else None


def main() -> None:
    env = read_env()
    results = []

    for label, prov, base, model, keyname in MODELS:
        key = env.get(keyname, "")
        if not key:
            print(f"[skip] {label}: 无 {keyname}")
            continue
        print(f"\n### {label}")
        cells = []
        for variant, padded in [("obvious", PADDED_OBVIOUS), ("subtle", PADDED_SUBTLE)]:
            for rnd, a_is in [(1, "concise"), (2, "padded")]:
                A, B = (CONCISE, padded) if a_is == "concise" else (padded, CONCISE)
                try:
                    txt = ask(base, key, model, PROMPT_TMPL.format(A=A, B=B))
                    letter = parse_choice(txt)
                except Exception as exc:  # noqa: BLE001
                    print(f"  [{variant} 轮{rnd}] 失败: {type(exc).__name__}: {str(exc)[:80]}")
                    cells.append(None)
                    continue
                if letter is None:
                    print(f"  [{variant} 轮{rnd}] 无法解析: {txt[:80]!r}")
                    cells.append(None)
                    continue
                chosen = A_is = a_is if letter == "A" else ("padded" if a_is == "concise" else "concise")
                print(f"  [{variant} 轮{rnd}] 位置A={a_is:<7} → {letter} = {chosen}")
                cells.append({"variant": variant, "rnd": rnd, "letter": letter, "chosen": chosen})
                time.sleep(4)  # 避让 RPM 限制
        results.append({"model": label, "cells": cells})

    # ── 汇总 ────────────────────────────────────────────────────────────
    print("\n" + "=" * 66)
    print("汇总")
    print("=" * 66)
    for variant in ("obvious", "subtle"):
        tot = pad = a_ = 0
        for r in results:
            for c in r["cells"]:
                if not c or c["variant"] != variant:
                    continue
                tot += 1
                if c["chosen"] == "padded":
                    pad += 1
                if c["letter"] == "A":
                    a_ += 1
        if tot:
            print(f"{variant:<8} 有效 {tot} 轮  |  注水胜率 {pad}/{tot} = {pad/tot:>4.0%}"
                  f"  |  选位置A {a_}/{tot} = {a_/tot:>4.0%}")

    out = Path("$HOME/.hermes/cache/scratch/judge_bias_result.json")
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n明细: {out}")


if __name__ == "__main__":
    main()
