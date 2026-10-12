# 安全改 /etc/docker/daemon.json (3046 实测教训, 2026-08-30)

## 背景
本会话改 docker 配置拉白名单外镜像(netmap), Hermes 手写 daemon.json 加错字段 → dockerd 启动失败 → 所有容器(homeassistant/photoprism/kuma/syncthing)全停。后派 Pi 写脚本(自动加 dockerd --validate + 备份恢复)一次成功。

## 正确代理格式 (docker ≥23.0)
```json
{
  "registry-mirrors": ["https://docker.m.daocloud.io"],
  "proxies": {
    "http-proxy":  "http://127.0.0.1:7890",
    "https-proxy": "http://127.0.0.1:7890",
    "no-proxy":    "localhost,127.0.0.1"
  }
}
```
- 错误: "proxies": { "default": {...} } —— dockerd 不认 default 键, 拒启动 (directives don't match any configuration option: default)
- 正确: 顶层键 "proxies", 子键 "http-proxy"/"https-proxy"/"no-proxy"

## 安全操作流程 (派 Pi 写脚本, Hermes 审完 sudo 执行)
1. 改前备份: sudo cp -a /etc/docker/daemon.json /etc/docker/daemon.json.bak.$(date +%s)
2. 写后验证: sudo dockerd --validate —— 不通过绝不 restart, 自动恢复备份退出
3. restart 后: docker info 确认 daemon 就绪, 再 docker ps 确认旧容器全 Up 才算完
4. cp 返回 0 不等于内容对: 本会话 cp 恢复却仍是错版, 故 restart 前必 dockerd --validate

## 零风险拉白名单外镜像 (不动 daemon.json)
3046 直连 Docker Hub 超时, 国内 mirror 白名单拦未知镜像。优先:
- 有网的机器(如台式机 .231)跑 docker pull img 再到 docker save img -o img.tar
- scp img.tar 到 3046 后 docker load -i img.tar
- 完全不动 daemon.json, 零炸 docker 风险

## NetMap 具体坑 (已删)
xoriin/netmap 镜像与 3046 docker cap_drop: ALL 不兼容: 容器内 nginx/uvicorn 切用户被拒 (failed switching to netmap: operation not permitted), PUID/PGID=0 和 tmpfs /tmp/nginx 都救不了。结论: 该镜像在 3046 跑不了, 删。
