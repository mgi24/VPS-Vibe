#!/bin/bash
set -e

if [ "$(id -u)" -ne 0 ]; then
    echo "Jalankan sebagai root: sudo bash install.sh"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DEFAULT_IF=$(ip route get 8.8.8.8 2>/dev/null | awk '{print $5}') || DEFAULT_IF="eth0"
DOMAIN="${1:-$(curl -s ifconfig.me 2>/dev/null || hostname -I | awk '{print $1}')}"

echo "=== WireGuard Free VPN Installer ==="
echo "Install dir : $SCRIPT_DIR"
echo "Interface   : $DEFAULT_IF"
echo "Domain/IP   : $DOMAIN"
echo ""

apt update
apt install -y wireguard iptables-persistent python3 python3-pip python3-venv sqlite3

cd "$SCRIPT_DIR"
if [ ! -d .venv ]; then
    python3 -m venv .venv
fi
.venv/bin/pip install -r requirements.txt

mkdir -p /opt/wireguardfree/clients
chmod 700 /opt/wireguardfree

if [ ! -f /etc/wireguard/server_private.key ]; then
    wg genkey | tee /etc/wireguard/server_private.key | wg pubkey > /etc/wireguard/server_public.key
    chmod 600 /etc/wireguard/server_private.key
fi
PRIV=$(cat /etc/wireguard/server_private.key)
PUB=$(cat /etc/wireguard/server_public.key)

if [ ! -f /etc/wireguard/wg0.conf ]; then
    cat > /etc/wireguard/wg0.conf << WGEOF
[Interface]
PrivateKey = ${PRIV}
Address = 10.0.0.1/24
ListenPort = 51820
PostUp = iptables -I FORWARD -i wg0 -o wg0 -j DROP
PostUp = iptables -A FORWARD -i wg0 -o ${DEFAULT_IF} -j ACCEPT
PostUp = iptables -t nat -A POSTROUTING -o ${DEFAULT_IF} -j MASQUERADE
PostUp = iptables -A FORWARD -i ${DEFAULT_IF} -o wg0 -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT
PostDown = iptables -D FORWARD -i wg0 -o wg0 -j DROP
PostDown = iptables -D FORWARD -i wg0 -o ${DEFAULT_IF} -j ACCEPT
PostDown = iptables -t nat -D POSTROUTING -o ${DEFAULT_IF} -j MASQUERADE
PostDown = iptables -D FORWARD -i ${DEFAULT_IF} -o wg0 -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT
SaveConfig = false
WGEOF
    echo "wg0.conf dibuat"
else
    echo "wg0.conf sudah ada, dilewati"
fi

echo "net.ipv4.ip_forward=1" > /etc/sysctl.d/99-wg.conf
sysctl -p /etc/sysctl.d/99-wg.conf

# Database dibuat otomatis oleh server.py saat startup

cat > /opt/wireguardfree/config.json << JSON
{
    "server_domain": "${DOMAIN}",
    "server_port": 51820,
    "server_pubkey": "${PUB}",
    "server_endpoint": "${DOMAIN}:51820",
    "subnet": "10.0.0.0/24",
    "wg_interface": "wg0",
    "wg_conf": "/etc/wireguard/wg0.conf",
    "db_path": "/opt/wireguardfree/data.db",
    "clients_dir": "/opt/wireguardfree/clients",
    "max_daily": 50,
    "max_per_session": 3,
    "dns_servers": ["1.1.1.1", "8.8.8.8"],
    "detected_interface": "${DEFAULT_IF}"
}
JSON

cat > /etc/systemd/system/wireguardfree.service << SERVICEEOF
[Unit]
Description=WireGuard Free Registration
After=network.target wg-quick@wg0.service

[Service]
Type=simple
WorkingDirectory=${SCRIPT_DIR}
ExecStart=${SCRIPT_DIR}/.venv/bin/uvicorn server:app --host 0.0.0.0 --port 8007
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
SERVICEEOF

systemctl daemon-reload
systemctl enable wg-quick@wg0 2>/dev/null || true
systemctl enable wireguardfree
systemctl start wg-quick@wg0 2>/dev/null || true
systemctl restart wireguardfree 2>/dev/null || true

iptables-save > /etc/iptables/rules.v4 2>/dev/null || true

echo ""
echo "=== Selesai! ==="
echo "Web       : http://$(hostname -I | awk '{print $1}'):8007"
echo "Endpoint  : ${DOMAIN}:51820"
echo ""
echo "Server Public Key: ${PUB}"
echo ""
echo "Catatan: Pastikan host meneruskan port UDP 51820 ke container ini"
echo "Contoh di host:"
echo "  iptables -t nat -A PREROUTING -i enp1s0 -p udp --dport 51820 -j DNAT --to-destination <IP_CONTAINER>:51820"
echo "  iptables -A FORWARD -p udp -d <IP_CONTAINER> --dport 51820 -j ACCEPT"
