# aider + GLM 调用模板（Windows / MSYS 环境）

## 坑（已踩）
1. PyPI 上 `aider` 是空壳包，真包是 `aider-chat`（命令名 `aider`）。装：`uv pip install aider-chat --python <venv>/Scripts/python.exe`
2. MSYS/bash 下 aider 报 `Can't initialize prompt toolkit: Found xterm-256color, expecting Windows console` → 必须走 `cmd.exe /c xxx.bat`，不可直跑
3. 模型名要带 provider 前缀：`zai/glm-4.7-flash`，且环境变量是 **`ZAI_API_KEY`**（不是 GLM_API_KEY）
4. 任务文本用 `--message "..."` 传；中文放 .bat 里，别在 bash `-c` 里传（会被拆成文件名）

## 模板 bat（精准改一个文件）
```bat
@echo off
setlocal
taskkill /f /im aider.exe 2>nul
cd /d H:\HermesShare\_aider_work
del /q target.py 2>nul
copy "C:\Users\<user>\AppData\Local\hermes\scripts\target.py" target.py >nul
for /f "tokens=2 delims==" %%k in ('findstr "^GLM_API_KEY=" "C:\Users\<user>\AppData\Local\hermes\.env"') do set ZAI_API_KEY=%%k
set PY=C:\Users\<user>\AppData\Local\hermes\hermes-agent\venv\Scripts\aider.exe
"%PY%" --model zai/glm-4.7-flash --no-auto-commit --no-git --yes --message "Describe the edit in English here." target.py
echo EXITCODE=%errorlevel%
endlocal
```
改 `target.py` 和 message 即可。跑：`cmd.exe /c run_aider.bat`

## 常驻封装（已落地）
`H:/HermesShare/aider_fix.bat <文件> "<英文任务>" [文件2...]`
