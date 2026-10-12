#!/usr/bin/env python3
"""上下文膨胀 / 调用延迟探针（只读，不改任何配置）。

回答一个问题：**「感觉慢」是模型慢、网络慢，还是输入太大**。
退出码约定：全正常 exit 0 打印 OK；有告警 exit 1 并把告警打到 stdout。

两条判据（详见 SKILL.md 铁律 26）：
  1. 阈值型配置不能看数值本身，要拿实际数据量反推它会不会触发。
     压缩阈值是「窗口的百分比」，窗口 512K + 阈值 0.75 ⇒ 触发线 38万 token；
     平均输入 12 万 ⇒ 压缩永远不会执行 —— 它不是失败了，是轮不到启动。
  2. in:out 比与平均输入 token 是「感觉慢」的第一手读数，比换模型早一步查。

延迟系数是单点拟合的经验值，不同 provider/模型差异大：只用来做量级判断
（几十秒 vs 几分钟），要精确值去看真实调用延迟字段或服务端日志。
"""
import os
import re
import sqlite3
import sys

DB = os.path.expanduser("~/.hermes/state.db")
CFG = os.path.expanduser("~/.hermes/config.yaml")

FIXED_S, PER_TOK_S = 2.0, 0.0005   # latency ≈ 固定开销 + 每 token 开销
LATENCY_BUDGET_S = 30.0            # 单次调用超过这个秒数就告警（按「能等多久」倒推）
INOUT_RATIO_WARN = 5.0             # in:out 超过这个值 = 上下文膨胀
WINDOWS = (131072, 262144, 524288, 1048576)


def cfg_get(text, key):
    """返回 (值, 命中的整行)。打印整行是为了让操作者确认匹配到哪一段——
    config.yaml 里有多个同名小节，只报值不报行等于让人盲信。"""
    for line in text.splitlines():
        m = re.match(rf"\s*{re.escape(key)}\s*:\s*(\S+)", line)
        if m:
            return m.group(1), line.strip()
    return None, None


def main():
    if not os.path.exists(DB):
        print(f"⚠️ 找不到 {DB}，无法测上下文膨胀")
        return 1
    # 只读打开体检库：探针绝不该有写路径
    c = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    alerts = []

    # ── 1. in/out 分布：输出少而输入巨大 = 上下文膨胀的第一手证据
    row = c.execute(
        "select coalesce(sum(api_call_count),0), coalesce(sum(input_tokens),0),"
        " coalesce(sum(output_tokens),0), avg(input_tokens), max(input_tokens)"
        " from session_model_usage"
    ).fetchone()
    calls, tin, tout, avg_in, max_in = row
    if not calls:
        print("⚠️ session_model_usage 无数据，无法测延迟")
        return 1

    ratio = tin / max(tout, 1)
    est_avg = FIXED_S + PER_TOK_S * avg_in
    print(f"调用 {calls:,} | 输入 {tin:,} tok | 输出 {tout:,} tok | in:out = {ratio:.1f}:1")
    print(f"单次输入 avg {avg_in:,.0f} → 预估 {est_avg:.1f}s | max {max_in:,.0f} tok")
    if ratio > INOUT_RATIO_WARN:
        alerts.append(f"in:out = {ratio:.1f}:1（>{INOUT_RATIO_WARN:.0f}）——输出少而输入巨大，典型上下文膨胀")
    if est_avg > LATENCY_BUDGET_S:
        alerts.append(f"平均每次调用预估 {est_avg:.1f}s，超预算 {LATENCY_BUDGET_S:.0f}s")

    # ── 2. 离群会话：单次输入远超 avg = 失控循环，不是正常上下文增长
    if max_in > avg_in * 20:
        alerts.append(f"max 输入 {max_in:,} 是 avg 的 {max_in/max(avg_in,1):.0f} 倍——查失控任务")
        print("\n疑似离群会话（单次输入 top5）：")
        for sid, mx in c.execute(
            "select session_id, max(input_tokens) from session_model_usage"
            " group by session_id order by mx desc limit 5"
        ):
            print(f"  {max(mx, 0):>12,} tok  {str(sid)[:40]}")

    # ── 3. 压缩阈值反推：阈值×窗口 vs 实际平均输入
    text = open(CFG, encoding="utf-8").read()
    th, th_line = cfg_get(text, "threshold")
    print()
    if th is None:
        alerts.append("config.yaml 找不到 compression.threshold——可能在用默认值")
    else:
        print(f"压缩阈值: {th_line}")
        if avg_in:
            print(f"实际平均输入 {avg_in:,.0f} tok。反推各窗口下的触发线：")
            for w in WINDOWS:
                trig = w * float(th)
                verdict = "触发不到（压缩等于没配）" if trig > avg_in else "可触发"
                print(f"  窗口 {w//1024:>4}K → 触发线 {trig:>9,.0f} tok  {verdict}")

    # ── 4. 主动裁剪的半配置状态：规则都配了，主开关是 0
    pp, pp_line = cfg_get(text, "proactive_prune_tokens")
    if pp is not None:
        print(f"主动裁剪: {pp_line}")
        if int(pp) == 0:
            has_rules = any(
                cfg_get(text, k)[0] not in (None, "0")
                for k in ("proactive_prune_min_result_chars",
                          "proactive_prune_min_reclaim_tokens")
            )
            if has_rules:
                alerts.append(
                    "proactive_prune_tokens=0 但裁剪规则已配——半配置状态："
                    "规则不会生效，大工具输出要等整体压缩才被砍"
                )
            else:
                alerts.append("proactive_prune_tokens=0——大工具输出从不主动裁剪")

    # ── 5. 进程重复拉起：与守护任务撞车会带走正在处理的请求
    out = os.popen("ps aux | grep -E '[h]ermes|[g]ateway' | wc -l").read().strip()
    print(f"\nhermes/gateway 相关进程: {out} 个")
    if out.isdigit() and int(out) > 6:
        alerts.append(f"{out} 个 hermes/gateway 相关进程——核对是否重复实例与守护任务撞车")

    print()
    if alerts:
        for a in alerts:
            print(f"🔴 {a}")
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())