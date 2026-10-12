#!/usr/bin/env bash
# pi_probe.sh — 探活 Pi 的所有 provider/model，分类报结论
#
# 为什么需要这个（2026-09-30 实测）：
#   1. Pi 配了 5 个 provider 7 个模型，但**可用性随账户状态变**，配置文件看不出来。
#   2. 失败长得完全不一样，人容易混淆：
#        429 rate_limit_reached_error      = 瞬时限流，**等几分钟就好，别删**
#        403 AllocationQuota.FreeTierOnly  = 免费额度耗尽，加钱或关「仅免费层」
#        1113 余额不足                      = 欠费，充值
#   3. **单次探活不足以定生死**：qwen3.7-plus 第一轮测是活的，几分钟后 403。
#      所以默认跑两轮，间隔 N 秒，只把「两轮都死」的标成 DEAD。
#
# 用法：
#   ~/.hermes/scripts/pi_probe.sh              # 两轮，默认间隔 60s
#   ~/.hermes/scripts/pi_probe.sh --once        # 单轮（快速）
#   ~/.hermes/scripts/pi_probe.sh --rounds 3    # 三轮
#   ~/.hermes/scripts/pi_probe.sh --json        # 机器可读输出
set -uo pipefail

ENV_FILE="$HOME/.pi/agent/.env"
MODELS_JSON="$HOME/.pi/agent/models.json"
[ -f "$ENV_FILE" ] && { set -a; . "$ENV_FILE"; set +a; }

ROUNDS=2; GAP=60; AS_JSON=0
while [ $# -gt 0 ]; do
  case "$1" in
    --once)   ROUNDS=1; shift;;
    --rounds) ROUNDS="$2"; shift 2;;
    --gap)    GAP="$2"; shift 2;;
    --json)   AS_JSON=1; shift;;
    *) echo "未知参数 $1"; exit 2;;
  esac
done

# 从 models.json 读，别硬编码（配置变了脚本要跟着活）
TARGETS=$(python3 - "$MODELS_JSON" <<'PY'
import json, sys
try:
    d = json.load(open(sys.argv[1]))["providers"]
except Exception as e:
    print(f"# 无法读取 {sys.argv[1]}: {e}", file=sys.stderr); sys.exit(0)
for prov, v in d.items():
    for m in v.get("models", []):
        print(f"{prov}\t{m.get('id')}")
PY
) || exit 1
[ -z "$TARGETS" ] && { echo "models.json 里没有可用 provider"; exit 1; }

# 分类：把 provider 的原始报错映射成明确结论
classify() {
  # 顺序很重要：**具体原因必须排在通用兜底前面**。
  # 2026-09-30 实测踩过：GLM 的欠费报错是 `429:{"code":"1113","message":"余额不足…"}`，
  # 429 兜底在前会把它判成「限流，等几分钟就好」—— 但它其实要充值，等多久都没用。
  # 判据错分类比不分类更危险：人会照着错结论等下去。
  case "$1" in
    *1113*|*余额不足*|*insufficient*|*余额*)   echo "UNPAID|欠费，充值后恢复" ;;
    *FreeTierOnly*|*free_tier*|*quota*)        echo "QUOTA|免费额度耗尽，加钱或控制台关「仅免费层」" ;;
    *rate_limit*|*RPM*)                        echo "RATELIMIT|瞬时限流，等几分钟重试，别删" ;;
    *401*|*unauthorized*|*Invalid*key*)        echo "BADKEY|key 失效或写错" ;;
    *404*|*"not found"*|*model_not*)           echo "NOMODEL|模型不存在/已下架" ;;
    *429*)                                     echo "RATELIMIT|限流（可能含额度上限）" ;;
    *)                                          echo "OTHER|见原始报错" ;;
  esac
}

probe_once() {   # $1=provider $2=model -> "OK" 或 "分类|说明"
  local out
  out=$(timeout 120 pi -p --provider "$1" --model "$2" --no-tools "只回复两个字：活着" 2>&1 | tail -1)
  if printf '%s' "$out" | grep -q "活着"; then echo "OK"; else classify "$out"; fi
}

declare -A RESULT   # "prov/model" -> "OK|分类"
declare -A NOTE
ORDER=()
while IFS=$'\t' read -r p m; do
  [ -n "$p" ] && ORDER+=("$p/$m")
done <<< "$TARGETS"

for r in $(seq 1 "$ROUNDS"); do
  [ "$r" -gt 1 ] && sleep "$GAP"
  for key in "${ORDER[@]}"; do
    p="${key%%/*}"; m="${key#*/}"
    res=$(probe_once "$p" "$m")
    if [ "$res" = "OK" ]; then
      RESULT[$key]="OK"
    else
      c="${res%%|*}"; d="${res#*|}"
      # 之前任何一轮成功过就算活的（单次失败可能是限流）
      [ "${RESULT[$key]:-}" = "OK" ] || { RESULT[$key]="$c"; NOTE[$key]="$d"; }
    fi
  done
done

if [ "$AS_JSON" = 1 ]; then
  python3 - "$ROUNDS" <<PY
import json, os
rounds = $ROUNDS
out = {}
for line in """$(printf '%s\n' "${ORDER[@]}")""".strip().split("\n"):
    if not line: continue
    out[line] = {"status": "${RESULT[$line]}"}
print(json.dumps({"rounds": rounds, "results": out}, ensure_ascii=False, indent=2))
PY
  exit 0
fi

echo "=== Pi provider 探活（$ROUNDS 轮）==="
for key in "${ORDER[@]}"; do
  case "${RESULT[$key]}" in
    OK)     printf "  ✅ %-34s 活\n" "$key" ;;
    *)      printf "  ❌ %-34s %-10s %s\n" "$key" "${RESULT[$key]}" "${NOTE[$key]}" ;;
  esac
done

dead=0
for key in "${ORDER[@]}"; do
  [ "${RESULT[$key]}" != "OK" ] && dead=$((dead+1))
done
echo
echo "  $(( ${#ORDER[@]} - dead ))/${#ORDER[@]} 活，$dead 死"
[ "$dead" -gt 0 ] && cat <<'TIP'

  ⚠️ DEAD 不等于 key 该删。按原因处理：
     RATELIMIT  → 什么都不用做，等几分钟（今天 qwen3.7-plus 第一轮活、第二轮 403）
     QUOTA      → 加钱，或控制台关「仅用免费层」
     UNPAID     → 充值
     BADKEY     → 这条才真的该换 key
     NOMODEL    → 配置里那条模型该删（模型本身没了）
TIP
exit 0
