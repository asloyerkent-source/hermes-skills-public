# 合并来源：software-development/local-coding-agents

> 由审计（skill-audit-20260918）合并自 `software-development/local-coding-agents`。原文保留如下。

---

---
name: local-coding-agents
description: aider+GLM and dsh on Windows; install traps, cost.
---

# Local Coding Agents (aider / dsh / GLM)

Two local options on this Windows host for agentic code work:

- **aider-chat + GLM-4.7-flash** — cheap/free precise pair-programmer. Best for single-file edits, bug fixes, small refactors. ~2–3k tokens/task.
- **DeepSeek Harness (dsh)** — autonomous multi-round agent loop. Best for complex multi-file tasks with self-test. BUT expensive now (see Cost Matrix).

## When to use which
- Small edit / fix / add a log line → aider + GLM (≈free, fast).
- Complex autonomous task with self-test loop → dsh headless (0.5–1.5元/task, acceptable only for high-value work).
- Never use dsh for daily small tweaks — output-token cost exploded.

## CRITICAL aider install trap
`pip install aider` installs a malicious/placeholder empty package (aider 0.2.6, no aider.exe entry point, only aider-install.exe). The real tool is:
```
uv pip install aider-chat --python "<venv>/Scripts/python.exe"
# entry point is aider.exe (not aider-chat.exe)
```
Verify: `aider.exe --version` → `aider 0.86.2`.

## Windows MSYS/git-bash launch fix
aider crashes under git-bash with:
`Can't initialize prompt toolkit: Found xterm-256color, while expecting a Windows console.`
Fix: wrap in a .bat and run via `cmd.exe /c run_aider.bat`. Do NOT invoke aider.exe directly from the bash terminal.

## GLM wiring (zai/ provider)
aider uses litellm; model names need a provider prefix and the right env var:
- Model: `zai/glm-4.7-flash` (NOT `glm-4-flash` → 404; NOT `deepseek-chat` bare → litellm "Provider NOT provided").
- Env: `ZAI_API_KEY` (value is the same GLM_API_KEY from `C:\Users\<user>\AppData\Local\hermes\.env`, but aider's zai provider reads `ZAI_API_KEY`, not `GLM_API_KEY`).
- Skip model warnings with `--no-show-model-warnings`.

### Reusable bat template
Copy `H:/HermesShare/aider_fix.bat` if present, or build from references/aider_glm_template.bat.

## dsh (DeepSeek Harness) eval notes
- Clone `deepseek-ai/deepseek-harness`, `pnpm install && pnpm build` (needs Node 22+, pnpm 11).
- Run headless: `pnpm dsh --profile headless "<task>"`.
- Needs `DEEPSEEK_API_KEY` exported in the launch env (it does NOT read Hermes .env). Pull from .env:
  `export DEEPSEEK_API_KEY=$(grep '^DEEPSEEK_API_KEY=' "$LOCALAPPDATA/hermes/.env" | head -1 | cut -d= -f2-)`
- dsh does NOT know your real architecture — it assumed 8642/8899/9119 all had /health and caused a false self-heal loop. Multi-model review + real curl probing caught it. Always verify its output against real host facts.

## Cost Matrix (real billing data, 2026-08-18)
User rule: costs must be REAL (from billing), never estimated. Reverse-engineered DS unit price:
- Input miss ≈1.04/M, input hit-cache ≈0.10/M, **output ≈10.30/M (5.2× old 2/M)**.
- dsh single task: ~0.5–1.5元 (agent loop inflates context to ~1M cached in + ~50k out).
- aider+GLM: ~free (GLM free tier).
- Lesson: for code editing, aider+GLM beats dsh 50–100× on cost.

## GLM direct-API pitfall (do NOT hand-roll)
Raw `requests.post('https://api.z.ai/v1/chat/completions', ...)` raises `urllib3 SSLError: UNEXPECTED_EOF_WHILE_READING`. The system proxy (7890) or GFW mid-path resets the direct TLS. aider routes through the proxy fine; a bare `requests` call does not.
Fix: don't call z.ai directly — use aider with `zai/glm-4.7-flash`. If a direct call is unavoidable, pass `proxies={'https':'http://127.0.0.1:7890'}`.

## PREFERRED model backend for aider + multi-model review: SiliconFlow (NOT GLM-direct)
User has a paid SiliconFlow account (`SILICONFLOW_API_KEY` in `.env`, ~10元 + 14元 free credit). It is the **stable, cheap, GFW-friendly** aggregation API (91 models, domestic direct-connect ~0.2s, no SSL reset).
- For aider: model `siliconflow/<model>` via litellm (e.g. `siliconflow/Qwen/Qwen3.5-35B-A3B`), env `SILICONFLOW_API_KEY`.
- For multi-model review / code audit: call **SiliconFlow** for the cheap reviewer (Qwen3.5-35B-A3B ~¥0.1/1M in, or the free Qwen2-7B layer at ¥0) and keep **DeepSeek (direct, `DEEPSEEK_API_KEY`)** as the second reviewer — user is happy with DS review cost. Do NOT use GLM-direct (SSL-fails) for review.
- Cost tiers (real SiliconFlow pricing, ¥/M tokens): free layer (Qwen2-7B/1.5B, GLM-4-9B) = ¥0; Qwen3.5-35B-A3B ≈ ¥0.1–0.3; DeepSeek-V3.2 ≈ ¥0.27 in / ¥1.0 out. Route: light tasks → free/9B layer; code/review → 35B MoE or DS; heavy reasoning → DS/122B occasionally.
- Principle: keep the cheap model as default for routine work; only spend on big models when the task justifies it. The user's 24元 balance lasts months at this routing.

## `.env` key-quoting bug (costs a 401, silent failure)
A `SILICONFLOW_API_KEY='sk-...'` line with **single quotes** makes Hermes's dotenv read the key *including* the quotes → API returns 401 Unauthorized even though the key is valid.
Fix: strip surrounding `'`/`"` when reading, and when writing `.env` never wrap secret values in quotes. Verified this session: removing the quotes on `SILICONFLOW_API_KEY` turned a 401 into a working 0.24s / 91-model response. Applies to any `*_API_KEY` line.

## Windows SSH-into-device credential quirks (remote exec on 3046/AX6S)
- `paramiko` SSH **fails with Authentication failed** on this host even with the correct password (dropbear ed25519 handshake quirk) — but the system `ssh` command connects fine. Use `ssh` via subprocess/wexpect, not paramiko.
- `wexpect` needs `pkg_resources` which setuptools≥81 removed → `import wexpect` dies with ModuleNotFoundError. Fix: `pip install "setuptools<81"` to restore pkg_resources, then wexpect works for interactive password feed.
- Ed25519 key auth is the clean path: generate a key pair, paste the **pubkey** into the device LUCI/authorized_keys (one manual step), then `ssh -i priv root@host` is passwordless forever. Used for AX6S; 3046 still blocked (sshd half-dead CLOSE_WAIT — needs user console).

## bat + cmd.exe pitfall (U-disk scripts)
A `.bat` double-clicked runs under `cmd.exe`, NOT bash. Bash heredoc `python - <<'PY'` and `$(...)`/`${VAR}` fail. For portable scripts (e.g. U-disk token injectors), put logic in a sibling `.py` and have the bat call `"%PY%" "%~dp0script.py"`. Verified this session: rewrote a laptop A2A injector this way, dry-run OK (url 31.159→2.159 + token written, other fields intact).

## Pitfalls (this host)
- `$HERMES_HOME` / `C:\Users\<user>` paths misbehave in MSYS bash — use literal `C:/Users/<user>` or `cmd.exe /c`.
- `python -c` with Chinese chars → exit 49 on Windows. Write a .py script file instead.
- `search_files` (rg) fails on `H:/HermesShare` (os error 3) — use terminal + ls/grep instead.
- DS bills on OUTPUT now — avoid any multi-round agent loop unless the task justifies it.
