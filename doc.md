# Service Documentation

| Service Name | Folder | Port | Nginx Domain |
|---|---|---|---|
| `portoweb.service` | `/home/mamad/portofolio` | 8003 | misbahwork.my.id |
| `yoloweb.service` | `/home/mamad/yolo` | 8004 | object.misbahwork.my.id |
| `webssh.service` | `/home/mamad/webssh` | 8002 | ssh.misbahwork.my.id |
| `vps.manager.service` | `/home/mamad/manage` | 8005 | manage.misbahwork.my.id |
| `diary.service` | `/home/mamad/diary` | 8006 | diary.misbahwork.my.id |
| `VPNweb.service` | `/home/mamad/VPNweb` | 8007 | vpn.misbahwork.my.id |
| `openwebui.service` | `/home/mamad/open-webui` | 8009 | chat.misbahwork.my.id |
| `9router` (Docker) | `/root/.9router` | 8012 | llm.misbahwork.my.id (rate limited) |
| `9router` (Docker) | `/root/.9router` | 8012 | 9r.misbahwork.my.id (unlimited, no blocklist) |
| `searxng` (Docker) | `/home/mamad/searxng` | 8013 | — |
| `filesharingweb.service` | `/home/mamad/webfile` | 8011 | — |
| `thingsboard.service` (Docker) | `/home/mamad/thingsboard` | 8080 | — |
| `sshd` | — | 8022 | — |
| `luckfox-tunnel` | SSH reverse tunnel (Luckfox Pico) | 8020 | luck.misbahwork.my.id |
| `mptcp.service` | `/usr/libexec/mptcpd` | system-level (MPTCP daemon) | — |
| `sing-box.service` | `/etc/sing-box/config.json` | 8881 (internal) | — |
| `socat-bridge.service` | `mptcpize + socat` | 8888 (MPTCP) | — |
| `iperf3` | — | 5201/tcp (default) | — |
| `iperf3-mptcp.service` | `mptcpize run iperf3` | 5202/tcp (MPTCP) | — |
| `camofox-browser.service` (Node.js) | `/home/mamad/camofox-browser` | 9377 | — |

| `hermes-gateway.service` | `/usr/local/lib/hermes-agent` | — | Discord bot gateway (no web UI) |
| `hermes-dashboard.service` | `/usr/local/lib/hermes-agent` | 8014 | — |
| `discord-notifier.service` | `/home/mamad/discord` | 8016 | — |
| `opencode.web` | `/home/mamad` | 8015 | auth: mamad / bajingan357 |


## ThingsBoard Exposed Ports (Docker)
- **8080** — HTTP Web UI (internal: 9090)
- **1883** — MQTT
- **7070** — Edge RPC
- **5683-5688/udp** — CoAP / LwM2M
- DB: PostgreSQL 12 (internal, port 5432, user/pass: `postgres`/`postgres`)

## Notes
- All services are **FastAPI** served via `uvicorn`, bare-metal (no Docker), kecuali ThingsBoard (Docker).
- Nginx reverse-proxies ports 80 → internal ports.
- `vps.manager` punya tab **WireGuard** untuk mengelola interface `wg-manage` (subnet 10.8.0.0/24, server 10.8.0.1, port UDP 51821, config `/etc/wireguard/wg-manage.conf`, meta peer `/etc/wireguard/wg-manage-meta.json`). VPNweb tetap di wg0/10.0.0.1 — tidak berubah.
- WebSSH & VPS Manager use Linux PAM authentication.
- `diary.service` requires PostgreSQL, credentials via `.env`.
- push git using: mgi24 email: ahmadmishbah@student.uns.ac.id

#REMOTE
## `persistent-route.service`
set ip rule and route for enp1s0

## iptables (manual rules)
```
# PREROUTING
DNAT  -i enp0s6 -j DNAT --to-destination 10.90.204.143

# POSTROUTING
MASQUERADE -o incusbr0 -j MASQUERADE
MASQUERADE -o enp0s6 -j MASQUERADE
MASQUERADE -o enp1s0 -j MASQUERADE

# FORWARD
ACCEPT -i enp0s6 -o incusbr0 -j ACCEPT
ACCEPT -i incusbr0 -o enp0s6 -j ACCEPT
```
