# 远程机器清理标准流程

## 触发
- 用户要求清理某台机器的磁盘空间
- 需要审计远程机器上运行的服务/程序
- 批量清理无用容器/服务/文件

## 执行流程（2026-09-02 3046清理实测）

### Phase 1: 诊断（只读）
```bash
# 1. 磁盘使用分析
df -h
du -sh /* | sort -rh | head -15
du -sh /home/* | sort -rh

# 2. 大文件识别（>100M）
find / -type f -size +100M 2>/dev/null | head -20

# 3. 运行服务审计
systemctl list-units --type=service --state=running
ss -tlnp  # 监听端口

# 4. Docker容器审计
docker ps -a
docker images
docker stats --no-stream

# 5. 手动安装包
apt-mark showmanual

# 6. Cron任务
crontab -l
ls /etc/cron.d/
```

### Phase 2: 分类识别
- **可安全清理**（无需确认）：旧日志、apt缓存、失效cron、临时脚本归档
- **需用户确认**：Python venv、研究项目、旧备份、未使用容器
- **保留**：核心服务、正在使用的容器、同步服务

### Phase 3: 方案呈现（等批准）
- 列出每项清理的预计释放空间
- 标注风险等级
- 等待用户确认大项

### Phase 4: 执行+验证
- 安全清理直接执行
- 每步验证：`df -h`/`docker ps`/`systemctl is-active`
- 清理后立即报对比数据

## 服务清理检查清单
- [ ] 蓝牙：服务器无蓝牙需求 → 禁用+卸载
- [ ] ModemManager：无3G/4G模块 → 禁用+卸载
- [ ] thermald：台式机非必需 → 可禁用
- [ ] 失效cron：每分钟执行但命令找不到 → 禁用
- [ ] 旧备份文件：确认有替代备份后删除
- [ ] 归档脚本：移入vault而非直接删

## 磁盘清理优先级
1. journal日志：`journalctl --vacuum-size=500M`
2. 旧轮转日志：`rm /var/log/syslog.* /var/log/kern.log.*`
3. apt缓存：`apt clean`
4. /tmp：`find /tmp -type f -mtime +3 -delete`
5. 截断当前大日志：`truncate -s 0 /var/log/syslog`

## 风险点
- **SMART告警**：清理前检查数据盘健康，避免在故障盘上操作
- **服务依赖**：禁用服务前确认无其他服务依赖
- **网络清理**：远程操作时避免清理网络相关服务导致失联
