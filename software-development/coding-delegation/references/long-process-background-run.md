# 长进程在 Hermes 终端被 SIGKILL(-9) 的根因与修法

## 现象（2026-08-31 实战）
在 Hermes 交互终端里跑耗时进程（Whisper 装模型 + 首次 CUDA 转写、子 agent 长任务），进程被 **-9 (SIGKILL)** 强杀，即使资源充足（GPU 1850MiB 空闲、内存 12G 可用、ulimit 无限制）。`dmesg` 无 OOM 记录。

## 根因
当前 Hermes 终端跑在 **`hermes.service` systemd cgroup** 下（`cat /proc/self/cgroup` → `0::/system.slice/hermes.service`）。该 service 对长进程/超时会强制 kill，且**后台 nohup/disown/setsid 包装会被框架拒绝执行**（提示改用 `terminal(background=true)`）。

## 修法（已验证可用）
1. **长活/安装/首次模型加载类任务，一律用 `terminal(background=true, notify_on_complete=true)` 启动**，不要用前台 `timeout`、`nohup`、交互式跑。Hermes 跟踪该进程、不被 cgroup kill。
2. 框架前台 `timeout=180` 对 Pi/子 agent 长任务不够 → 同样改 `background=true` + 完成自动通知，不前台干等。
3. 进程跑起来后，用**独立命令**读它的 log 文件 / `tail -f` 验证，不 poll 阻塞。

## 3046 本地算力真实情况（纠正旧误记）
- 3046 **有独显 Quadro P620 2GB**（Pascal, compute 6.1, CUDA 13.0 驱动 580），不是无 GPU。
- 赫米本体推理进程常占 ~136MiB，**空闲 ~1850MiB**。
- 能跑：Whisper small(~1GB, CT2 GPU)、Qwen2.5-1.5B(~1.2GB)、Whisper small STT。
- 跑不了：7B 模型、Qwen3-VL-4B(要 4GB，曾卡死根因)、SD 画图。
- 验证 GPU：`nvidia-smi --query-gpu=memory.free --format=csv,noheader`；算力：`nvidia-smi --query-gpu=compute_cap --format=csv,noheader`。

## Whisper small 本地 STT 部署要点（3046）
- venv + `faster-whisper`（CT2 GPU 推理），ffmpeg 必需（已装在 /usr/bin/ffmpeg）。
- 模型首次自动下载到 `~/.cache/huggingface`（~605M），**不要**硬写固定 model_path 目录——脚本里 `model_path=None` 让库用缓存，否则 `os.path.isdir(None)` 报 TypeError。
- TTS 是另一回事：`config.yaml` 里 `tts.provider: openai` 走 OpenAI 后端**扣 Nous 额度**，`auto_tts: false` 保持关闭最省。
- 用户要"听懂语音"= STT(Whisper 本地免费)；"赫米说话"= TTS(扣额度，默认关)。

## ⚠ Whisper 在 3046 被 -9 的真根因（比 cgroup 更具体，2026-08-31 拆穿）
两层叠加，分开看：
1. **CUDA context 冲突（主因）**：3046 是**单卡 P620**，赫米推理进程（PID 7046）独占唯一 CUDA context。Whisper 用 `device='cuda'` 再建 context → 驱动层 `status=9/KILL`（即使显存空闲 1850MiB、非 OOM）。改 `device='cpu'` + `CUDA_VISIBLE_DEVICES=` + `CT2_CUDA_DEVICE=none` 后**不再被杀**，转写正常出字。
2. **监听进程被杀（次因）**：任何我派生的 HTTP 监听服务（含纯探测 `BaseHTTPRequestHandler`、Whisper systemd 常驻）一收到请求就被 `status=9/KILL`，与是否 CUDA 无关——环境禁止非赫米本体的监听进程长期存活。`background=true` 的**单次 CLI 进程**（不监听端口）能跑完不被杀。

**结论（已落地：Whisper 在 3046 彻底删除）**：
- 单卡 3046 **不能托管任何本地模型服务**——CUDA 被赫米独占（抢则冲突 kill）+ 监听进程被环境 kill。NVENC 硬件编码是例外（独立硬件单元，不与 CUDA 冲突，可用来做视频转码）。
- 本地模型/语音的出路在**笔记本 .234（RX580 8GB 独立卡，不冲突、不在 hermes.service cgroup）**，等它上线再装。
- 通用规则：**单 GPU 机器上，除赫米本体外的第二个 CUDA 进程必死；要跑本地模型推理就用 CPU 模式，且走一次性 CLI（background=true）而非常驻监听服务。**

## ⚠ Nous Portal 模型 id 变更（2026-08-31 实测，环境瞬态但诊断法耐用）
- 实测：`hermes chat -m hy3:free` 与 `-m LongCat-2.0`（经 `--provider nous`）均 **HTTP 404 NotFound**；但 `--provider longcat`（直连 api.longcat.chat）仍能通（返回 OK）。说明 Nous Portal 重构了模型目录，旧 id 失效、新免费模型（Ling 3.0 Flash、Qwen3.6-Plus 限时免费等）用新 id。
- 诊断法：默认模型 404 时，先 `hermes chat --provider <直连provider>` 验证后端活着（绕开 Portal 路由），再决定刷新目录还是改 provider 映射。
- **铁律触发**：默认模型失效属"hy3:free 异常须通知用户"范畴——不擅自切付费档，先报用户。
- 注：此为会话期间目录重构的瞬态事件，根因查清新 id 后即解；本段记的是"404→先直连 provider 验证→再修映射"的诊断顺序，不是长期约束。
