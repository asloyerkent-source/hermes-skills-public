@echo off
REM aider + GLM 精准代码编辑封装 (零成本, 不走DS)
REM 用法: aider_fix.bat <目标文件> "<任务描述(英文)>"  [额外文件...]
REM 例: aider_fix.bat H:\HermesShare\foo.py "Fix the timeout bug in bar()" H:\HermesShare\bar.py
REM
REM 坑(已踩, 必记):
REM  1. aider pip 包名是 aider-chat (不是同名空壳 aider; 装错无 aider.exe 入口)
REM  2. 模型用 zai/glm-4.7-flash + 环境变量 ZAI_API_KEY (不是 GLM_API_KEY)
REM  3. aider 在 git-bash/MSYS 下 prompt toolkit 报错 -> 必须走 cmd.exe /c 本bat
setlocal
taskkill /f /im aider.exe 2>nul
cd /d %~dp0
if "%~2"=="" (
  echo 用法: aider_fix.bat ^<文件^> ^"<任务(英文)>" [文件2...]
  exit /b 1
)
set "TARGETS=%*"
set "MSG=%~2"
set "FILES=%~1"
set "REST="
set "skip=1"
for %%a in (%*) do (
  if !skip!==0 set "REST=!REST! %%a"
  set /a skip-=1
)
for /f "tokens=2 delims==" %%k in ('findstr "^GLM_API_KEY=" "C:\Users\<user>\AppData\Local\hermes\.env"') do set ZAI_API_KEY=%%k
set PY=C:\Users\<user>\AppData\Local\hermes\hermes-agent\venv\Scripts\aider.exe
"%PY%" --model zai/glm-4.7-flash --no-auto-commit --no-git --yes --message "%MSG%" %FILES% %REST%
echo EXITCODE=%errorlevel%
endlocal
