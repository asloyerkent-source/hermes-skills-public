# 诊断/根因多模型验证 — 实操笔记 (2026-08-16)

## 触发原则
用户: "你的诊断再多模型看看，不要盲目下判断，glm优先"。
即: 网络/设备/性能类根因, 先实测抓数据, 再 GLM(优先)+DS 审, agent 不自下结论。

## Windows 网络实测抓取技巧 (powershell 中文编码坑多, 用 python+psutil/netstat 更稳)
- 进程: `tasklist /FO CSV /NH` 后正则筛 clash|verge|oray|zerotier|wireguard
- 端口监听: `netstat -ano | findstr :7890` (看 LISTENING 的 0.0.0.0 vs 127.0.0.1)
- 路由表: `route print -4` (看 0.0.0.0/0 几条、是否被抢)
- 全部网卡(含虚拟): `wmic nic get Name,NetConnectionStatus` 或 `Get-NetAdapter -IncludeHidden`
- 系统代理: 读注册表 `HKCU:/Software/Microsoft/Windows/CurrentVersion/Internet Settings` 的 ProxyEnable/ProxyServer
- DNS: `ipconfig /all` 抓 DNS 服务器行 (注意只看 IPv4 还是仅 IPv6)
- 直连测试: python `socket.create_connection(('api.telegram.org',443),3)` 看是否超时 (移动CGNAT直连境外常超时)
- PowerShell 含中文时 `$_.Name` 会被 shell 误解析 → 改用 python subprocess 调 tasklist/netstat 最稳

## 本次实例 (台式网络乱象 + TG失联)
事实清单(实测):
1. 物理网卡 Realtek 192.168.99.X, 网关 31.1
2. 默认路由仅1条 0.0.0.0/0->31.1 (无抢占)
3. 系统代理 ProxyEnable=1, 127.0.0.1:7890 (Clash Verge 系统代理模式)
4. Clash 监听 0.0.0.0:7890 (LAN可连, 非仅127)
5. PID 13420 持续14+连 7890 + 连 123.59.191.x:443 (TG MTProto段)
6. 蒲公英 OrayBoxVpnEnt 网卡未连接、无进程
7. DNS 仅 IPv6 fd76:da8a:7100::1, 无 IPv4 DNS
8. 用户说"移动大内网"= 移动宽带CGNAT无公网IP (非虚拟网卡! 曾误判)

双模型结论(一致):
- Clash 是"症状放大器"非根因; 更根本 = CGNAT无公网IP + 单点代理出口(代理抖=全断)
- "移动大内网"误判纠正: 是运营商NAT, 不是软件虚拟网卡 (实测无TAP/TUN/ZeroTier)
- TG失联根因 = 单点故障: TG网关(PID13420)流量全走127.0.0.1:7890, 直连TG超时, 代理抖即挂
- 致命陷阱: 监控告警绝不能依赖 TG 本身 (TG挂时TG告警也发不出) → 改本地Windows通知/邮件
- 治理: ① Clash监听改127 ② DNS固化IPv4 ③ NO_PROXY内网直连 ④ 3046远程访问等刷OpenWrt走路由WireGuard/ZeroTier(3046本机不装VPN) ⑤ 代理健康监控

## 复用产物实例
- 笔记本已写 `OpenWrt刷机计划.md` + `ax6s_fw/` 四件套固件(factory/sysupgrade/recovery/ubi-loader), sha256与官方一致 → 直接复用+双模型补审, 不重写
- 缺口: OpenWrtInvasion解锁脚本 + Tftpd64 救砖工具 未下 (到场前补)
