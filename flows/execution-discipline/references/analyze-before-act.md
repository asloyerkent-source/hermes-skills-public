# 工作流纪律：先分析再动手

## 问题类任务（报错/修复/调试）标准流程

1. **先读官方文档/源码**：查本地 docs、搜源码关键词，搞清楚正确配置方式
2. **再多模型分析**：用 ≥2 个模型交叉分析根因，定位问题
3. **再派 Pi 执行**：分析定稿后，派 Pi 写修复脚本/改配置
4. **最后 Hermes 验证**：Pi 产出后读真文件 + 真跑命令确认

## 反例：微信 proxy error 400

### 错误做法
用户说"回复 proxy error 400"，我直接跳到改配置：
- 改 mihomo 路由规则 → 无效
- 改 .env HTTP_PROXY → 无效
- 改 systemd service → 无效
- 改 .bashrc → 无效
- 改 config.yaml 全局 proxy_url → 这个其实是对的，但当时没验证就继续往下走了

### 正确做法
1. 先读官方文档 `website/docs/user-guide/messaging/weixin.md`
2. 再读源码 `gateway/platforms/weixin.py`，发现 `trust_env=True`
3. 分析日志：`api_calls=0` 说明 LLM API 调用没成功，不是微信 API 的问题
4. 定位根因：config.yaml 全局 `proxy_url` 把 LongCat LLM API 推给 mihomo
5. 派 Pi 删全局 proxy_url，保留 telegram 平台代理
6. 验证：gateway 重启后环境变量只剩 `TELEGRAM_PROXY`

## 判别标准

| 任务类型 | 正确流程 |
|---------|---------|
| 报错/修复/调试 | 读文档/源码 → 多模型分析 → Pi 执行 → Hermes 验证 |
| 新建/功能开发 | 直接 Pi 写 |
| 简单查询/配置读 | Hermes 自己做 |

## 关键线索

- `api_calls=0` → LLM API 调用根本没成功
- `Proxy error (400) from http://127.0.0.1:7890` → 代理问题，不是目标 API 问题
- 日志里 `trust_env=True` → 走环境变量代理
