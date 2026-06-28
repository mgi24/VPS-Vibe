# WireGuard Free VPN

## Instalasi

```bash
cd /home/mamad/wireguardfree
sudo bash install.sh [domain-atau-ip-anda]
```

> Argumen opsional: domain/IP untuk endpoint WireGuard. Default: IP publik.

## Service

| Service | Description |
|---------|-------------|
| `wireguardfree.service` | Web app (FastAPI + uvicorn) port **8007** |
| `wg-quick@wg0.service` | WireGuard interface **wg0** port **51820** |

### Manajemen Service

```bash
sudo systemctl status wireguardfree     # Cek status
sudo systemctl restart wireguardfree    # Restart web
sudo systemctl start wireguardfree      # Start
sudo systemctl stop wireguardfree       # Stop
sudo journalctl -u wireguardfree -f     # Log realtime
```

Untuk WireGuard:
```bash
sudo wg show                            # Lihat peer
sudo systemctl restart wg-quick@wg0     # Restart wg
```

## Akses

- **Web:** `http://<ip>:8007/`
- **Admin:** `http://<ip>:8007/admin`
- **Download config:** `http://<ip>:8007/download/<nama_file>.conf`

## Rate Limit

- **50 akun/hari** (global, reset otomatis tiap hari)
- **3 akun/session browser** (tracking via cookie `session_id`)
- **3 akun/IP** (fallback jika cookie dihapus)

## WireGuard

- Subnet: `10.0.0.0/24`
- Server IP: `10.0.0.1`
- Client: `10.0.0.2` – `10.0.0.254`
- Port: `51820` (UDP)
- DNS: `1.1.1.1`, `8.8.8.8`

### Block peer-to-peer

Peer tidak bisa saling komunikasi — di-block oleh iptables:
```
iptables -I FORWARD -i wg0 -o wg0 -j DROP
```

### Konfigurasi

- Server keys: `/etc/wireguard/server_private.key` / `server_public.key`
- Server config: `/etc/wireguard/wg0.conf`
- App config: `/opt/wireguardfree/config.json`
- Database: `/opt/wireguardfree/data.db`
- Client configs: `/opt/wireguardfree/clients/`

> **Catatan:** Karena VPS di Incus, host harus mem-forward **UDP 51820** ke IP container:
> ```bash
> iptables -t nat -A PREROUTING -i enp1s0 -p udp --dport 51820 -j DNAT --to-destination <IP_CONTAINER>:51820
> iptables -A FORWARD -p udp -d <IP_CONTAINER> --dport 51820 -j ACCEPT
> ```

## Database

```bash
sqlite3 /opt/wireguardfree/data.db "SELECT COUNT(*) FROM accounts;"
sqlite3 /opt/wireguardfree/data.db "SELECT * FROM accounts ORDER BY id DESC LIMIT 10;"
sqlite3 /opt/wireguardfree/data.db "SELECT * FROM global_daily;"
```
