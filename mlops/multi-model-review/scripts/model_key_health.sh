#!/usr/bin/env bash
# model_key_health.sh — 多模型探活脚本
# 用途：每次跑多模型评审前，先用 10 token 快速探活，确认 ≥3 个模型可用

set -euo pipefail
set -a; source $HOME/.hermes/.env; set +a

ALIVE=0
FAILED=0

check() {
  local model=$1 endpoint=$2 key=$3 extra_args=${4:-}
  local resp http_code
  resp=$(curl -s --max-time 15 -w "\n%{http_code}" -X POST "https://$endpoint/chat/completions" \
    -H "Authorization: Bearer $key" \
    -H "Content-Type: application/json" \
    -d "{\"model\":\"$model\",\"messages\":[{\"role\":\"user\",\"content\":\"ok\"}],\"max_tokens\":10${extra_args}}" 2>/dev/null)
  http_code=$(echo "$resp" | tail -1)
  if [ "$http_code" = "200" ]; then
    echo "✅ $model @ $endpoint"
    ALIVE=$((ALIVE + 1))
  else
    echo "❌ $model @ $endpoint → HTTP $http_code"
    FAILED=$((FAILED + 1))
  fi
}

# 直连（五路并行池）
check deepseek-chat api.deepseek.com/v1 "$DEEPSEEK_API_KEY"
check glm-5.2 open.bigmodel.cn/api/paas/v4 "$GLM_API_KEY"
check qwen3.7-plus dashscope.aliyuncs.com/compatible-mode/v1 "$DASHSCOPE_API_KEY"
check kimi-k2.7-code api.moonshot.cn/v1 "$KIMI_API_KEY" ',"temperature":1'
check LongCat-2.0 api.longcat.chat/openai/v1 "$LONGCAT_API_KEY"

echo "---"
echo "存活: $ALIVE | 失败: $FAILED"
if [ $ALIVE -ge 3 ]; then
  echo "PROCEED — ≥3 模型可用"
  exit 0
else
  echo "HALT — <3 模型可用，跳过评审"
  exit 1
fi
