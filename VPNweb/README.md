# WireGuard Free — Web Register VPN

Web registrasi WireGuard VPN gratis.  
Jalan di **port 8007**, subnet **`10.0.0.0/16`** (65.534 IP).

## Stack

- **FastAPI** + **Uvicorn** (systemd: `VPNweb.service`)
- **SQLite** (`/opt/wireguardfree/data.db`)
- **Jinja2** templates

## Fitur

- Generate config via browser → download `.conf`
- **50 global registrasi/hari**, **3 per session cookie/hari**
- Progress bar kuota harian (biru → merah)
- Peer-to-peer diblokir (iptables `DROP wg0→wg0`)

## Reset Rate Limit

Jalankan sebagai **root**:

```bash
sudo python3 reset.py
```

Ini hapus semua limit session & harian — user bisa register lagi tanpa tunggu besok.

## Struktur

```
├── server.py         # FastAPI app (routes: /, /generate, /download, /my, /admin)
├── reset.py          # Reset rate limit
├── install.sh        # One-shot instalasi
├── requirements.txt
├── templates/
│   ├── index.html
│   ├── my_configs.html
│   └── admin.html
└── README.md
```

## Instalasi

```bash
sudo bash install.sh
```

Service otomatis jalan via systemd.
