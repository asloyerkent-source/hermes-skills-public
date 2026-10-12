# Direct GLM / DeepSeek API cookbook (verified 2026-08-16)

Call these **directly**, not through Nous Portal (Nous Portal 404s GLM models and
wastes Nous credits reserved for Sonnet).

## GLM (free tier, Z.AI / 智谱)
- **Endpoint (WORKS):** `https://open.bigmodel.cn/api/paas/v4/chat/completions`
- **Endpoint (DEAD — 404):** `https://api.z.ai/v1/...` and `https://api.z.ai/api/paas/v4/...`
  (both return nginx 404; do NOT use `api.z.ai`).
- Key: `GLM_API_KEY` from `~/.hermes/.env` (the **free** key; RPM-limited, not token-limited).
- Models: `glm-4.5-air`, `glm-4.7` / `glm-4.7-flash`.
- **Reasoning content:** GLM returns `message.reasoning_content` (a long chain-of-thought
  block) that can eat the token budget and leave `content` short/empty. When you only
  want the answer, either (a) read `message.content` and ignore `reasoning_content`, or
  (b) keep `max_tokens` modest (≤2000) and ask for concise output.
- **Minimal Python:**
  ```python
  import re, requests
  key = re.search(r'^GLM_API_KEY\s*=\s*(.+)',
                  open(r'C:/Users/<user>/AppData/Local/hermes/.env',
                       encoding='utf-8', errors='ignore').read(), re.M).group(1).strip().strip('"').strip("'")
  r = requests.post(
      "https://open.bigmodel.cn/api/paas/v4/chat/completions",
      headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
      json={"model": "glm-4.5-air", "messages": [{"role": "user", "content": PROMPT}],
            "temperature": 0.3, "max_tokens": 4000},
      timeout=180)
  print(r.json()["choices"][0]["message"]["content"])
  ```
- **Bypass proxy** (these are domestic APIs; if the client inherits `HTTP_PROXY` it
  SSL-fails intermittently): pass `proxies={"http": None, "https": None}` to
  `requests.post`, or `os.environ` strip `HTTP(S)_PROXY` before the call.

## DeepSeek (user-PAID / 充值 key — bills their balance, NOT free tier)
- Endpoint: `https://api.deepseek.com/v1/chat/completions`
- Key: `DEEPSEEK_API_KEY` from `.env` (paid; describe as "DeepSeek paid key, direct calls").
- Model: `deepseek-v4-flash` (or `deepseek-chat`).
- Same proxy-bypass note as GLM.

## Free-tier behavior (GLM especially)
- Expect `429` and **empty `content`** on longer outputs (model truncates to length,
  reasoning fills budget). Mitigations: short `max_tokens`, exponential backoff
  (12–20s × 5–8), low-peak scheduling. Don't burn credits retrying forever.
- Verify before trusting: `r.json()["choices"][0]["message"]["content"]` may be absent
  on free tier — handle KeyError / empty.
- Buying more GLM *tokens* does NOT raise RPM (requests/min). The RPM wall is separate.

## HuggingFace / Model downloads on 3046
- **3046 has no direct internet.** Outbound traffic must go through the local Clash proxy
  (mihomo, port 7890). HuggingFace (huggingface.co, github.com) is NOT reachable by default.
- `transformers`, `requests`, `urllib` all inherit the `HTTP_PROXY` / `HTTPS_PROXY` env vars.
  On 3046 this routes them through Clash, and HTTPS to huggingface.co frequently times out
  even when `curl -sI -x http://127.0.0.1:7890 https://huggingface.co` works fine.
- **Diagnose first:**
  - `curl -sI --noproxy '*' https://huggingface.co` → "Network is unreachable" = confirmed no direct path
  - `curl -sI -x http://127.0.0.1:7890 https://huggingface.co` → 200 OK = proxy path works
  - If proxy path works but Python still times out: the library is picking up a stale proxy
    variable, or the proxy itself is overloaded.
- **Fix options (in order):**
  1. **Set `HF_ENDPOINT=https://hf-mirror.com`** in env and use that mirror.
  2. **Ensure `HTTP_PROXY` / `HTTPS_PROXY` are UNSET** in the running process (many Hermes
     scripts unset them to bypass Clash for domestic APIs, which then breaks ALL outbound
     including HuggingFace).
  3. **Use `curl` + manual cache placement** for model downloads — bypass Python libraries
     entirely.
- **Verify network before declaring failure:** `nslookup huggingface.co` resolving only
  proves DNS is fine. TCP connectivity through the proxy is the actual requirement.
- **PyTorch version trap (P620):** Quadro P620 is CUDA capability 6.1. PyTorch ≥2.1
  requires CC 7.5+. Must use `torch==2.0.1+cu117`. PyTorch 2.0 also doesn't support
  Python 3.12 — create a Python 3.11 venv:
  `python3.11 -m venv $HOME/.venvs/moondream`.