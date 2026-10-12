# 五模型全并行 v4 —— 生产模板与加权共识

> **本文件是 `multi-model-review` 技能的支持文档。**
> 来源：2026-09-26 从 SKILL.md 下沉（原「生产模板：五模型全并行 v4」+「加权共识算法」两节）；并合原 `references/parallel-curl-template.md`（bash curl 模板）。**两处是同一件事，此处合一，勿再分家。**

---

## 生产模板：五模型全并行 v4
### 如何实现真正的多模型并行（关键）—— 五模型全并行 v4

> **本章 2026-09-16 重写（v4）**。起因：一次 DeepSeek 独立审查在 v3 方案里挑出 F1–F7 共 7 处缺陷，逐条修完后写成 v4。
> **被废弃的旧设计**：v3 之前的"两阶段串行 + 阈值短路"设计（Phase 1 串行跑 3 个模型，够数就短路不跑 Phase 2）**已废弃**，不要再照抄。旧设计的核心错误见本章末尾踩坑记录 F1/F2。
> **delegate_task 为什么不行**：`delegate_task` **无法做多模型审核** —— subagent 继承的是系统默认模型，你在 task 里写"请用 Kimi 审"也没用，实际执行的还是默认那一个模型。要做真·多模型，只能在 shell 里对**每个模型各起一个 curl 进程**，显式指定各自的 endpoint + model + key。这就是本章全部设计的由来。
### 五模型全并行策略（2026-09-16 v4）

**核心思想**：不要串行、不要两阶段。**五个模型一次性全部并行发出**，谁先回谁先落盘，最后统一收口算加权票。串行的账很好算：90s（DeepSeek）+ 45s（Kimi）= 135s，而全并行最坏只等于最慢那个模型，即 **90s**，白省 45s。所谓"两阶段省钱"是假的 —— 见 F2。

**生产参数表（总权重 10）**：

| 模型 | model | endpoint | keyenv | weight | timeout | max_tokens | temperature |
|------|-------|----------|--------|--------|---------|-----------|-------------|
| DeepSeek（主审） | `deepseek-chat` | `https://api.deepseek.com/v1` | `DEEPSEEK_API_KEY` | **3** | 90 | 1000 | 0.3 |
| GLM-5.2 | `glm-5.2` | `https://open.bigmodel.cn/api/paas/v4` | `GLM_API_KEY` | **2** | 45 | 1000 | 0.3 |
| Qwen3.7+ | `qwen3.7-plus` | `https://dashscope.aliyuncs.com/compatible-mode/v1` | `DASHSCOPE_API_KEY` | **2** | 45 | 1000 | 0.3 |
| Kimi | `kimi-k2.7-code` | `https://api.moonshot.cn/v1` | `KIMI_API_KEY` | **2** | 45 | 800 | **1** |
| LongCat | `LongCat-2.0` | `https://api.longcat.chat/openai/v1` | `LONGCAT_API_KEY` | **1** | 30 | 500 | 0.3 |

- 权重之和 = 3+2+2+2+1 = **10**（共识阈值因此一律写作 "x/10"）。
- **Kimi 必须 `temperature=1`**：传 0.3 等值直接报 400。
- **DeepSeek 主审权重 3**、GLM-5.2 二审 2、Qwen3.7+ 三审 2、Kimi 二审 2、LongCat 兜底 1（免费但不顶主审）。原 HY3 与 MiniMax 均已移出池：HY3 免费档已过期（付费版另计），MiniMax 从未配置端点。
- **Kimi 限 3 RPM**：直连 `api.moonshot.cn` 每分钟仅 3 次请求，全并行时最易 429；失败即跳过，不重试（铁律 1）。
- **LongCat 直连**：`https://api.longcat.chat/openai/v1`（官方直连，免费资源包），key `LONGCAT_API_KEY`，model `LongCat-2.0`。等价备用通道是 Nous 平台的 `meituan/longcat-2.0:free`（`inference-api.nousresearch.com/v1`，`NOUS_API_KEY`）。
- **GLM-5.2 max_tokens 限制**：Pi 调用时 max_tokens >150 会导致响应 >12s 超时。轻任务设 max_tokens=150 以内，或改用 Qwen3.7+ / DeepSeek 做长输出。
- 端点全部来自本文档「当前可用 key」章节，不得自行编造。
### 关键实现：curl 错误处理（F3 修复）+ 统一配置表（F6 修复）

**F3 的坑**：旧写法 `curl -s -X POST ... -w '%{http_code}'` 把 **stderr 混进 body 文件**，又把 HTTP 状态码**追加在 body 末尾**，然后 `tail -1` 去取码 —— body 里任何换行都能让 `tail -1` 取错行；接着 `json.load()` 抛异常，`extract_text()` 把异常吞掉后**静默返回空字符串**。空响应和"模型真的没意见"从此再也分不清。

**F3 的修法**：用 `-o "$body"` 把响应体单独落盘，用 `-w '%{http_code}'` 把状态码写进 stdout 并重定向到 `$code`，stderr 单独进 `$err`；检查函数从 **`.code` 文件**读码，**绝不用 `tail -1`**；并把四种失败显式区分成 `EMPTY / HTTP xxx / TIMEOUT(28) / PARSE_FAIL`，其中 **JSON 解析失败绝不能退化成空字符串**。

**完整脚本（五模型全并行 + 加权共识）—— 原样搬自 A（实现侧技能 SKILL.md），未删改；`EP[glm]` 块在原文件里出现两次（内容相同，GLM 直连/free 额度），照实保留：**

```bash
# ============================================================
# 五模型全并行交叉审核 v4  ——  生产模板
# 退出码: 0 = 达成共识(最终加权票 >= 6 且 verdict 非空)
#         1 = 未达成/仅部分一致(需人工介入)
# ============================================================
set -uo pipefail
set -a; source $HOME/.hermes/.env; set +a   # 加载各模型 key

WORK="${WORK:-/tmp/mmcr_$(date +%s)}"; mkdir -p "$WORK"

# ---------- 统一配置表 (F6 修复: 加模型 = 每张表加一行) ----------
declare -A EP MODEL KEYENV TEMP MAXTOK TIMEOUT WEIGHT
MODELS=(deepseek glm qwen kimi longcat)

EP[deepseek]="https://api.deepseek.com/v1";            MODEL[deepseek]="deepseek-chat"
KEYENV[deepseek]="DEEPSEEK_API_KEY";                   TEMP[deepseek]=0.3
MAXTOK[deepseek]=1000;  TIMEOUT[deepseek]=90;          WEIGHT[deepseek]=3

EP[glm]="https://open.bigmodel.cn/api/paas/v4";        MODEL[glm]="glm-5.2"
KEYENV[glm]="GLM_API_KEY";                             TEMP[glm]=0.3
MAXTOK[glm]=1000;       TIMEOUT[glm]=45;               WEIGHT[glm]=2

EP[qwen]="https://dashscope.aliyuncs.com/compatible-mode/v1"; MODEL[qwen]="qwen3.7-plus"
KEYENV[qwen]="DASHSCOPE_API_KEY"; TEMP[qwen]=0.3
MAXTOK[qwen]=1000; TIMEOUT[qwen]=45; WEIGHT[qwen]=2

EP[kimi]="https://api.moonshot.cn/v1";                 MODEL[kimi]="kimi-k2.7-code"
KEYENV[kimi]="KIMI_API_KEY";                           TEMP[kimi]=1      # Kimi 必须 =1; 限 3 RPM
MAXTOK[kimi]=800;       TIMEOUT[kimi]=45;              WEIGHT[kimi]=2

EP[glm]="https://open.bigmodel.cn/api/paas/v4";        MODEL[glm]="glm-5.2"
KEYENV[glm]="GLM_API_KEY";                             TEMP[glm]=0.3      # GLM 直连，免费额度
MAXTOK[glm]=1000;       TIMEOUT[glm]=45;               WEIGHT[glm]=2

EP[longcat]="https://api.longcat.chat/openai/v1";      MODEL[longcat]="LongCat-2.0"
KEYENV[longcat]="LONGCAT_API_KEY"; TEMP[longcat]=0.3
MAXTOK[longcat]=500; TIMEOUT[longcat]=30; WEIGHT[longcat]=1
# 👆 加一个模型 = 上面这 6 行样式各加一遍 + MODELS 数组加个名字, 不改别的代码

PROMPT="${1:?用法: $0 <审核任务/待审内容>}"

# prompt 契约: 必须输出 JSON, 字段名固定为 verdict, 取值三选一
read -r -d '' ASK <<'EOF' || true
你是独立审核方。请只输出一行合法 JSON, 不要 markdown 代码块, 不要多余文字:
{"verdict":"APPROVE|REJECT|MODIFY","reason":"一句话理由","findings":["最高危问题"]}
verdict 含义: APPROVE=可放行; REJECT=有阻断问题; MODIFY=方向对但必须先改。
EOF

# ---------- 单模型调用: 每个模型一个独立后台进程 (F3 修复) ----------
call_model() {  # $1=模型键  $2=prompt文本
  local k="$1" ep="${EP[$1]}" key="${!KEYENV[$1]:-}" t="${TIMEOUT[$1]}"
  local body="$WORK/$k.body" code="$WORK/$k.code" err="$WORK/$k.err" pid="$WORK/$k.pid"
  local ask="$2"
  echo $$ > "$pid"

  if [ -z "$ep" ] || [ -z "$key" ]; then
    printf 'SKIP_NO_ENDPOINT_OR_KEY' > "$code"; : > "$body"; return 0
  fi

  # 组装请求体 (按模型参数) 写入临时文件
  python3 - "$k" "${MODEL[$k]}" "${TEMP[$k]}" "${MAXTOK[$k]}" "$ask" <<'PY' > "$WORK/$k.req"
import json,sys
k,model,temp,mt,ask=sys.argv[1],sys.argv[2],float(sys.argv[3]),int(sys.argv[4]),sys.argv[5]
print(json.dumps({"model":model,"temperature":temp,"max_tokens":mt,"stream":False,
  "messages":[{"role":"system","content":ask},{"role":"user","content":ask}]},
  ensure_ascii=False))
PY

  # ⚠️ 关键: -o body / -w code / 2> err 三路分离; 绝不把状态码追加进 body
  # -d @"$WORK/$k.req" 从文件读请求体, 绝不读 stdin (后台进程 stdin = /dev/null 会立即 EOF)
  curl -sS --max-time "$t" -X POST "$ep/chat/completions" \
    -H "Authorization: Bearer ${!KEYENV[$1]}" -H "Content-Type: application/json" \
    -d @"$WORK/$k.req" -o "$body" -w '%{http_code}' > "$code" 2> "$err" &
  local curlpid=$!
  wait "$curlpid"
  local rc=$?
  [ "$rc" -eq 28 ] && printf 'TIMEOUT(28)' > "$code"      # 显式标注超时
  [ "$rc" -ne 0 ] && [ "$rc" -ne 28 ] && printf 'CURL_ERR(%s)' "$rc" > "$code"
  return 0
}

# ---------- 错误判定: 从 .code 文件读码, 不用 tail -1 ----------
check_model() {  # $1=模型键; 回显状态: OK / SKIP / EMPTY / HTTP xxx / TIMEOUT(28) / PARSE_FAIL
  local k="$1" body="$WORK/$1.body" code="$WORK/$1.code"
  local code_val
  code_val=$(cat "$code" 2>/dev/null)          # ← F3: 只读 .code 文件, 绝不 tail -1

  case "$code_val" in
    ''|CURL_ERR*|SKIP*)  echo "SKIP";                          return 1 ;;
    TIMEOUT*)            echo "TIMEOUT(28)";                   return 1 ;;
    2[0-9][0-9])         : ;;
    *)                   echo "HTTP $code_val";                return 1 ;;
  esac

  if [ ! -s "$body" ]; then echo "EMPTY"; return 1; fi

  # JSON 解析失败 → PARSE_FAIL, 绝不静默变空串 (F3 核心)
  python3 - "$body" 2>/dev/null <<'PY' || { echo "PARSE_FAIL"; return 1; }
import json,sys
d=json.load(open(sys.argv[1],encoding='utf-8'))
c=(d.get('choices') or [{}])[0].get('message',{}).get('content')
r=(d.get('choices') or [{}])[0].get('message',{}).get('reasoning_content')
txt=(c or r or '').strip()
sys.exit(0 if txt else 1)                       # 解析成功但内容空 → 也算不可用
PY
  echo "OK"; return 0
}

# ---------- 一轮全并行: 五个模型同时发 ----------
run_all() {
  local ask="$1" k
  for k in "${MODELS[@]}"; do call_model "$k" "$ask" & done
  wait                                            # 全并行, 耗时=最慢模型(90s)
}

# ---------- 取 verdict: JSON 优先, 正则兜底 (F5 + F7 修复) ----------
get_verdict() {  # $1=模型键; stdout=APPROVE|REJECT|MODIFY|UNKNOWN, 并回显权重
  local k="$1" body="$WORK/$1.body"

  # 1) 先按 JSON 解析, 且只读顶层 verdict 键
  local v
  v=$(python3 - "$body" 2>/dev/null <<'PY'
import json,sys,re
try:
    d=json.load(open(sys.argv[1],encoding='utf-8'))
    msg=(d.get('choices') or [{}])[0].get('message',{}) or {}
    raw=(msg.get('content') or msg.get('reasoning_content') or '')
except Exception:
    sys.exit(3)                                  # → 交给正则兜底
# content 可能是被 ``` 包裹或夹带解释的 JSON, 抠出第一个 {...}
m=re.search(r'\{.*\}', raw, re.S)
if m:
    try:
        obj=json.loads(m.group(0))
        val=obj.get('verdict')                   # ← 只认顶层 verdict 键
        if isinstance(val,str): print(val); sys.exit(0)
    except Exception:
        pass
print(raw.strip()[:200])                         # 非 JSON → 原文交给 normalize
PY
)
  # 2) 正则兜底: 仅在 JSON 解析失败/未取到 verdict 时使用
  if [ -z "$v" ] || [ "$v" = "3" ]; then
    v=$(grep -oiE '\b(APPROVE|REJECT|MODIFY)\b' "$body" 2>/dev/null | head -1)
  fi

  # 3) 归一化: 不在 {APPROVE,REJECT,MODIFY} 一律 UNKNOWN
  local up; up=$(printf '%s' "$v" | tr '[:lower:]' '[:upper:]')
  case "$up" in
    *APPROVE*) echo "APPROVE" ;;
    *REJECT*)  echo "REJECT"  ;;
    *MODIFY*)  echo "MODIFY"  ;;
    *)         echo "UNKNOWN" ;;
  esac
}

# ---------- 加权共识: 绝对票数制, 10 分标尺 (不是比例!) ----------
consensus() {  # $1..= vote_bucket 结果
  declare -A bucket=( [APPROVE]=0 [REJECT]=0 [MODIFY]=0 )
  local valid_w=0 k v w
  for k in "${MODELS[@]}"; do
    v=$(get_verdict "$k"); w="${WEIGHT[$k]}"
    if [ "$v" = "UNKNOWN" ]; then
      continue                       # ← F7: UNKNOWN 绝不进票桶, 也不进分母
    fi
    bucket[$v]=$(( bucket[$v] + w ))
    valid_w=$(( valid_w + w ))
  done

  # 找最高票
  local top="" topw=0
  for v in APPROVE REJECT MODIFY; do
    if [ "${bucket[$v]}" -gt "$topw" ]; then top="$v"; topw="${bucket[$v]}"; fi
  done

  echo "票型: APPROVE=${bucket[APPROVE]}  REJECT=${bucket[REJECT]}  MODIFY=${bucket[MODIFY]}"
  echo "有效权重: ${valid_w}/10   最高票: ${top} = ${topw}/10"

  if   [ "$topw" -ge 6 ] && [ -n "$top" ]; then
    echo "结论: $top  —— 采纳 (high confidence)"; return 0
  elif [ "$topw" -ge 4 ]; then
    echo "结论: 部分一致 ($topw/10) —— medium confidence, 需人工复核"; return 1
  else
    echo "结论: 未达成共识 ($topw/10) —— low confidence"; return 1
  fi
}

mkdir -p "$WORK"; echo "工作目录: $WORK"
run_all "$PROMPT"
for k in "${MODELS[@]}"; do printf '%-9s %s\n' "$k" "$(check_model "$k")"; done
consensus
exit $?     # 0 = 达成共识 (加权票>=6 且 verdict 非空); 1 = 其他情况
```
## 加权共识算法（绝对票数制）

**必须用绝对票数，不能用比例。** 旧版写的是"占比 ≥ 0.6 即采纳 / ≥ 0.8 强一致"这类**比例规则**，已删除 —— 在 5 个模型、3 票就过半的场景里，比例规则会让 4/10 甚至 3/10 直接冒充共识，绕过了主审权重设计。改为固定 10 分标尺：

| 加权票数 | 判定 | 置信度 | 处置 |
|---------|------|--------|------|
| **≥ 6 / 10** | 采纳 | high confidence | 直接采信该 verdict |
| **4–5 / 10** | 部分一致 | medium confidence | **需人工复核**，不自动放行 |
| **< 4 / 10** | 未达成共识 | low confidence | 按"无结论"处理，升级人工 |

- 分母是**有效权重之和**（跳过 SKIP/UNKNOWN 的模型），不是固定的 10；但输出时同时打印 `有效权重: N/10`，方便一眼看出有几个模型真上线了。
- `UNKNOWN` **绝不投进任何票桶**，也**不计入分母权重**（F7）。
- 典型算例：DeepSeek(3)+Kimi(2)+GLM-5.2(2) 都给 REJECT = **7/10 → 采纳**；只有 DeepSeek(3)+LongCat(1) = 4/10 → **部分一致，需人工**。
### Findings 共识（权重累加）

verdict 投票只回答"整体放不放行"。**同一条 finding 被多个模型指出**时，用权重累加判断它是不是真问题：

| 组合 | 累加权重 | 可信度 |
|------|---------|--------|
| DeepSeek + GLM-5.2 | 5 | 极高 |
| DeepSeek + Qwen3.7+ | 5 | 极高 |
| DeepSeek + Kimi | 5 | 极高 |
| DeepSeek + LongCat | 4 | 高 |
| GLM-5.2 + Qwen3.7+ | 4 | 高 |
| Kimi + GLM-5.2 | 4 | 高 |
| GLM-5.2 + LongCat | 3 | 中 |
| Kimi + LongCat | 3 | 中 |
| 仅单模型 | 1-3 | 仅供参考，不单独采纳 |

- 同一 finding 的识别按**位置 + 问题类型**归并（不能只按文字相似度，措辞不同但指的是同一处要并成一条）。
- 累加权重 ≥4 的 finding 视为**已确认问题**，必须写进结论；单模型的 finding 只列"单模型主张"，不得单独作为定论。
- 权重低但指出**崩溃/丢数据**类风险的 finding，无论权重多少都要写进结论（与 verdict 一致：权重只用于排序，不用于压制少数）。
### 输出契约（prompt contract）

要求每个模型**只输出一行合法 JSON**：

```json
{"verdict":"APPROVE|REJECT|MODIFY","reason":"一句话理由","findings":["最高危问题"]}
```

- 字段名固定 `verdict`，三个取值 `APPROVE | REJECT | MODIFY`。**不要用 `stance` 或其他字段名**。
- 解析顺序：**先 JSON**（只读顶层 `verdict` 键）→ 失败才**正则兜底** → 归一化，三者之外一律 `UNKNOWN`（F5/F7）。
- `get_verdict` 读 DeepSeek 内容时遵循铁律 6：`content or reasoning_content`。

---

# 多模型并行评审：bash curl 模板（五模型全并行）

## 何时用
用户说"多模型分析论证下"，且任务需要经验判断（方案评审、风险识别、可行性分析）。

## 要点
- delegate_task 继承默认模型，无法真正多模型。必须并行 curl 直接调 API。
- **五模型全并行**：DS + GLM-5.2 + Qwen3.7+ + Kimi + LongCat 同时发出，wait 等最慢的（90s）。
- **Kimi 直连 api.moonshot.cn，限 3 RPM** —— 但 5 路并行时只发 1 次请求，不触发限流；失败即跳过
- prompt 含中文用 `jq -n --arg p "$PROMPT"` 转义，避免控制字符 400。
- Prompt 契约：所有模型返回 JSON `{verdict, confidence, findings}`
- curl 结果三文件分离：body / .err / .code

## 完整脚本（五模型全并行 + 加权共识）

```bash
#!/usr/bin/env bash
set -euo pipefail
set -a; source $HOME/.hermes/.env; set +a

PROMPT=$(cat << 'PROMPT_EOF'
[审核目标 + 约束条件]
Reply ONLY JSON: {"verdict":"APPROVE|REJECT|MODIFY","confidence":0.0-1.0,"findings":[{"id":"F1","severity":"P0|P1|P2","description":"..."}]}
PROMPT_EOF
)

# curl 结果三文件分离：body / .err / .code
check_model() {
  local name=$1 out=$2
  if [ ! -s "$out" ]; then echo "$name: EMPTY"; return 1; fi
  local code=$(cat "${out}.code" 2>/dev/null || echo "000")
  if [ "$code" != "200" ]; then echo "$name: HTTP $code"; return 1; fi
  return 0
}

extract_text() {
  python3 -c "
import json
with open('$1') as f:
    d=json.load(f)
msg=d['choices'][0]['message']
print(msg.get('content') or msg.get('reasoning_content') or '')
" 2>/dev/null || echo ""
}

get_verdict() {
  echo "$1" | python3 -c "
import sys, json
r=sys.stdin.read().strip()
if not r:
    print('UNKNOWN'); sys.exit(0)
try:
    v=json.loads(r).get('verdict','')
    if v in ('APPROVE','REJECT','MODIFY'):
        print(v)
    else:
        print('UNKNOWN')
except:
    print('UNKNOWN')
" 2>/dev/null
}

# 五模型并行
DS_OUT=/tmp/review_ds.json; GLM_OUT=/tmp/review_glm.json
QW_OUT=/tmp/review_qw.json; KM_OUT=/tmp/review_km.json; LC_OUT=/tmp/review_lc.json

curl_call() {
  local model=$1 endpoint=$2 key=$3 prompt=$4 outfile=$5 extra=$6
  curl -s --max-time 90 -w "%{http_code}" -X POST "$endpoint/chat/completions" \
    -H "Authorization: Bearer ***" -H "Content-Type: application/json" \
    -d "$(jq -n --arg p "$prompt" "{\"model\":\"$model\",\"messages\":[{\"role\":\"user\",\"content\":\"$p\"}],\"max_tokens\":1000${extra}}")" \
    > "$outfile" 2>"${outfile}.err"
  echo "$?" > "${outfile}.code"
}

curl_call deepseek-chat api.deepseek.com/v1 "$DEEPSEEK_API_KEY" "$PROMPT" "$DS_OUT" &
curl_call glm-5.2 open.bigmodel.cn/api/paas/v4 "$GLM_API_KEY" "$PROMPT" "$GLM_OUT" ',"max_tokens":1000' &
curl_call qwen3.7-plus dashscope.aliyuncs.com/compatible-mode/v1 "$DASHSCOPE_API_KEY" "$PROMPT" "$QW_OUT" ',"max_tokens":1000' &
curl_call kimi-k2.7-code api.moonshot.cn/v1 "$KIMI_API_KEY" "$PROMPT" "$KM_OUT" ',"temperature":1,"max_tokens":800' &
curl_call LongCat-2.0 api.longcat.chat/openai/v1 "$LONGCAT_API_KEY" "$PROMPT" "$LC_OUT" ',"max_tokens":500' &
wait

DS_TXT=$(check_model DeepSeek "$DS_OUT" && extract_text "$DS_OUT") || DS_TXT=""
GLM_TXT=$(check_model GLM "$GLM_OUT" && extract_text "$GLM_OUT") || GLM_TXT=""
QW_TXT=$(check_model Qwen "$QW_OUT" && extract_text "$QW_OUT") || QW_TXT=""
KM_TXT=$(check_model Kimi "$KM_OUT" && extract_text "$KM_OUT") || KM_TXT=""
LC_TXT=$(check_model LongCat "$LC_OUT" && extract_text "$LC_OUT") || LC_TXT=""

DS_V=$(get_verdict "$DS_TXT"); GLM_V=$(get_verdict "$GLM_TXT"); QW_V=$(get_verdict "$QW_TXT")
KM_V=$(get_verdict "$KM_TXT"); LC_V=$(get_verdict "$LC_TXT")

# 加权投票 — UNKNOWN 不计入权重
declare -A W
for v_w in "$DS_V:3" "$GLM_V:2" "$QW_V:2" "$KM_V:2" "$LC_V:1"; do
  IFS=: read -r v w <<< "$v_w"
  [ "$v" != "UNKNOWN" ] && W[$v]=$(( ${W[$v]:-0} + w ))
done

FINAL=""; FW=0
for v in "${!W[@]}"; do [ "${W[$v]}" -ge 6 ] && FINAL=$v && FW=${W[$v]}; done

# 退出码：0=达成共识, 1=未达成/需人工复核
if [ -z "$FINAL" ]; then
  echo "未达成共识（权重不足 6/10）"
  echo "DS=$DS_V, GLM=$GLM_V, QW=$QW_V, KM=$KM_V, LC=$LC_V"
  exit 1
fi

echo "══════════════════════════════════════"
echo "加权共识: $FINAL (权重: $FW/10)"
echo "══════════════════════════════════════"
echo "DS($DS_V,×3): $DS_TXT"
echo "GLM($GLM_V,×2): $GLM_TXT"
echo "QW($QW_V,×2): $QW_TXT"
echo "KM($KM_V,×2): $KM_TXT"
echo "LC($LC_V,×1): $LC_TXT"
exit 0
```

## 结论汇总规则

- 加权票数 ≥6 → 采纳（高置信）
- 加权票数 4-5 → 部分一致（中置信，需人工复核）
- 加权票数 <4 或全分歧 → 未达成共识（低置信，列出所有发现供人工判断）
- 空响应/404/timeout → 标记该模型不可用，不重试
- UNKNOWN 不计入加权权重

---

## ⚠️ 本文件含两套 bash 实现，以哪套为准？

1. **上半部分**（原 SKILL.md「生产模板：五模型全并行 v4」+「加权共识算法」）—— **v4 定稿版，以它为准**；F1–F7 修复（curl 错误处理、统一配置表、加权共识绝对票数制）都在这里。
2. **下半部分**（原 `parallel-curl-template.md`，2026-09-26 已合并进本文件、原件删除）—— 更早的 curl 模板，**保留作对照与精简参考**。两者仅共享 6 行，内容互补非重复；新写脚本请基于第 1 套。
