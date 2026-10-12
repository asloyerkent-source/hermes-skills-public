# -*- coding: utf-8 -*-
"""三阶段多模型流水线模板: HY3草稿 → GLM深加工 → DeepSeek审核 (静默落文件)
用法: 复制改 JOBS 与资料包路径即可。cron no_agent 跑，不刷屏。

2026-08-19 修正:
  - GLM 端点改为 open.bigmodel.cn (原 api.z.ai 实测404, 见 cookbook)
  - 内容读取 content or reasoning_content (GLM免费档常把正文放 reasoning_content,
    只读 content 会拿到空串导致空重试/超时)
"""
import requests, time, os

HERMES_HOME = os.environ.get("HERMES_HOME", r"C:\Users\<user>\AppData\Local\hermes")
OUT = r"H:\HermesShare"
LOG = os.path.join(HERMES_HOME, "pipeline.log")

def log(m):
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {m}\n")

def _key(prefix):
    for line in open(os.path.join(HERMES_HOME, ".env"), encoding="utf-8", errors="ignore"):
        if line.strip().startswith(prefix):
            return line.strip().split("=", 1)[1].strip()
    return None

def _text(msg):
    # 双字段兜底：GLM免费档正文常在 reasoning_content
    return (msg.get("content") or msg.get("reasoning_content") or "").strip()

def glm(prompt, max_tok=800):
    k = _key("GLM_API_KEY=")
    if not k:
        log("  GLM无key"); return None
    for i in range(6):
        try:
            r = requests.post("https://open.bigmodel.cn/api/paas/v4/chat/completions",
                headers={"Authorization": f"Bearer {k}", "Content-Type": "application/json"},
                json={"model": "glm-4.5-air", "messages": [{"role": "user", "content": prompt}],
                      "temperature": 0.3, "max_tokens": max_tok}, timeout=180,
                proxies={"http": None, "https": None})
            r.raise_for_status()
            t = _text(r.json().get("choices", [{}])[0].get("message", {}))
            if t:
                return t
            time.sleep(15 * (i + 1))
        except Exception as e:
            log(f"  GLM异常: {str(e)[:40]}")
            time.sleep(15 * (i + 1))
    # GLM 优先策略: 3个月免费期内优先用; 全失败则兜底切 SiliconFlow (用户充值10元保底)
    log("  GLM 6次失败, 兜底切 SiliconFlow")
    return sf_fallback(prompt, max_tok)

def sf_fallback(prompt, max_tok=800):
    k = _key("SILICONFLOW_API_KEY=")
    if not k:
        log("  SF无key"); return None
    try:
        r = requests.post("https://api.siliconflow.cn/v1/chat/completions",
            headers={"Authorization": f"Bearer {k}", "Content-Type": "application/json"},
            json={"model": "Qwen/Qwen3.5-35B-A3B", "messages": [{"role": "user", "content": prompt}],
                  "temperature": 0.3, "max_tokens": max_tok}, timeout=180,
            proxies={"http": None, "https": None})
        r.raise_for_status()
        t = _text(r.json().get("choices", [{}])[0].get("message", {}))
        if t:
            log("  SF兜底成功(Qwen3.5-35B)")
            return t
    except Exception as e:
        log(f"  SF兜底异常: {str(e)[:40]}")
    return None

def ds(prompt, max_tok=500):
    k = _key("DEEPSEEK_API_KEY=")
    if not k:
        log("  DS无key"); return None
    try:
        r = requests.post("https://api.deepseek.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {k}", "Content-Type": "application/json"},
            json={"model": "deepseek-v4-flash", "messages": [{"role": "user", "content": prompt}],
                  "temperature": 0.3, "max_tokens": max_tok}, timeout=180,
            proxies={"http": None, "https": None})
        r.raise_for_status()
        return _text(r.json().get("choices", [{}])[0].get("message", {}))
    except Exception as e:
        log(f"  DS异常: {str(e)[:40]}")
        return None

# (src_hy3, glm_out, ds_out, task_name)  — 资料包全文喂入，不截断
PKG = open(os.path.join(OUT, "三项目资料包.md"), encoding="utf-8", errors="ignore").read()
JOBS = [
    ("阶段1落实手册_HY3.md", "阶段1落实手册_GLM.md", "阶段1落实手册_DS审.md", "任务①阶段1落实手册"),
]

for src, glm_out, ds_out, task in JOBS:
    sp = os.path.join(OUT, src)
    if not os.path.exists(sp):
        continue
    base = open(sp, encoding="utf-8", errors="ignore").read()
    log(f"处理 {src}")
    glm_r = glm(f"基于完整资料包对该任务深加工，遵守全局纪律与已定决策：\n{PKG}\n\n草稿：\n{base}\n\n产出：命令级步骤+验证+坑+回滚，1000字内。", 1000)
    if glm_r:
        open(os.path.join(OUT, glm_out), "w", encoding="utf-8").write(glm_r)
        log(f"  GLM {glm_out} ({len(glm_r)}字)")
        ds_r = ds(f"基于资料包审方案可行性/遗漏/命令正确性：\n{PKG[:2000]}\n\n待审：\n{glm_r}")
        if ds_r:
            open(os.path.join(OUT, ds_out), "w", encoding="utf-8").write(ds_r)
            log(f"  DS {ds_out} ({len(ds_r)}字)")
    else:
        log(f"  GLM失败 {src}")
    time.sleep(10)
log("流水线结束")
