#!/usr/bin/env python3
import os, sys, json, sqlite3, subprocess, uuid, ipaddress
from datetime import date
from pathlib import Path
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from urllib.parse import quote
from fastapi.templating import Jinja2Templates

if os.geteuid() != 0:
    print("ERROR: Jalankan sebagai root (sudo)", file=sys.stderr)
    sys.exit(1)

BASE = Path(__file__).parent
CFG_PATH = "/opt/wireguardfree/config.json"

with open(CFG_PATH) as f:
    cfg = json.load(f)

DB_PATH = cfg["db_path"]
WG_CONF = cfg["wg_conf"]
WG_IFACE = cfg["wg_interface"]
SUBNET = ipaddress.IPv4Network(cfg["subnet"])
SERVER_PUBKEY = cfg["server_pubkey"]
SERVER_ENDPOINT = cfg["server_endpoint"]
CLIENTS_DIR = Path(cfg["clients_dir"])
MAX_DAILY = cfg["max_daily"]
MAX_SESSION = cfg["max_per_session"]
DNS = cfg["dns_servers"]

CLIENTS_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="MMV VPN")
templates = Jinja2Templates(directory=str(BASE / "templates"))
app.mount("/assets", StaticFiles(directory=str(BASE / "assets")), name="assets")


def get_db():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA journal_mode=WAL")
    return db


def init_db():
    db = get_db()
    db.executescript("""
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            private_key TEXT NOT NULL,
            public_key TEXT NOT NULL,
            address TEXT NOT NULL UNIQUE,
            session_id TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            created_date TEXT DEFAULT (date('now'))
        );
        CREATE TABLE IF NOT EXISTS rate_limits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            identifier TEXT NOT NULL,
            date TEXT NOT NULL,
            count INTEGER DEFAULT 1,
            UNIQUE(identifier, date)
        );
        CREATE TABLE IF NOT EXISTS global_daily (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT UNIQUE NOT NULL,
            count INTEGER DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS config (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
    """)
    try:
        db.execute("ALTER TABLE accounts ADD COLUMN session_id TEXT")
    except sqlite3.OperationalError:
        pass
    db.execute("INSERT OR IGNORE INTO config (key, value) VALUES ('next_ip', '2')")
    db.commit()
    db.close()


def get_next_ip(db):
    row = db.execute("SELECT value FROM config WHERE key = 'next_ip'").fetchone()
    idx = int(row["value"]) if row else 2
    max_idx = 65534  # 10.0.255.254
    while idx <= max_idx:
        ip = f"10.0.{idx // 256}.{idx % 256}"
        if not db.execute("SELECT 1 FROM accounts WHERE address = ?", (ip,)).fetchone():
            db.execute("INSERT OR REPLACE INTO config (key, value) VALUES ('next_ip', ?)", (str(idx + 1),))
            return ip
        idx += 1
    return None


def check_limits(db, sid, ip):
    today = date.today().isoformat()
    row = db.execute("SELECT count FROM global_daily WHERE date = ?", (today,)).fetchone()
    if row and row["count"] >= MAX_DAILY:
        return False, "Kuota hari ini penuh (50/50). Coba besok!"
    if sid:
        row = db.execute("SELECT count FROM rate_limits WHERE identifier = ? AND date = ?",
            (f"session:{sid}", today)).fetchone()
        if row and row["count"] >= MAX_SESSION:
            return False, "Kamu sudah 3x daftar hari ini (per session)."
    row = db.execute("SELECT count FROM rate_limits WHERE identifier = ? AND date = ?",
        (f"ip:{ip}", today)).fetchone()
    if row and row["count"] >= MAX_SESSION:
        return False, "IP ini sudah 3x daftar hari ini."
    return True, ""


def increment_limits(db, sid, ip):
    today = date.today().isoformat()
    db.execute("""INSERT INTO global_daily (date, count) VALUES (?, 1)
        ON CONFLICT(date) DO UPDATE SET count = count + 1""", (today,))
    if sid:
        db.execute("""INSERT INTO rate_limits (identifier, date, count) VALUES (?, ?, 1)
            ON CONFLICT(identifier, date) DO UPDATE SET count = count + 1""",
            (f"session:{sid}", today))
    db.execute("""INSERT INTO rate_limits (identifier, date, count) VALUES (?, ?, 1)
        ON CONFLICT(identifier, date) DO UPDATE SET count = count + 1""",
        (f"ip:{ip}", today))


def gen_keys():
    priv = subprocess.check_output(["wg", "genkey"]).strip().decode()
    pub = subprocess.check_output(["wg", "pubkey"], input=priv.encode()).strip().decode()
    return priv, pub


def add_peer(pubkey, addr):
    subprocess.run(["wg", "set", WG_IFACE, "peer", pubkey, "allowed-ips", f"{addr}/32"], check=True)
    with open(WG_CONF, "a") as f:
        f.write(f"\n[Peer]\nPublicKey = {pubkey}\nAllowedIPs = {addr}/32\n")


def gen_conf(client_priv, client_addr):
    return f"""[Interface]
PrivateKey = {client_priv}
Address = {client_addr}/32
DNS = {', '.join(DNS)}

[Peer]
PublicKey = {SERVER_PUBKEY}
Endpoint = {SERVER_ENDPOINT}
AllowedIPs = 0.0.0.0/0
PersistentKeepalive = 25
"""


def daily_left(db):
    today = date.today().isoformat()
    row = db.execute("SELECT count FROM global_daily WHERE date = ?", (today,)).fetchone()
    return max(0, MAX_DAILY - (row["count"] if row else 0))


# --- Routes ---

@app.get("/", response_class=HTMLResponse)
async def index(request: Request, config: str = "", error: str = ""):
    sid = request.cookies.get("session_id") or uuid.uuid4().hex
    db = get_db()
    try:
        total = db.execute("SELECT COUNT(*) as c FROM accounts").fetchone()["c"]
        ctx = {
            "request": request,
            "max_daily": MAX_DAILY,
            "max_session": MAX_SESSION,
            "quota_left": daily_left(db),
            "total_accounts": total,
            "error": error,
            "success": False,
            "conf_file": "",
            "conf_content": "",
        }
        if config:
            fpath = CLIENTS_DIR / config
            if fpath.exists():
                ctx["success"] = True
                ctx["conf_file"] = config
                ctx["conf_content"] = fpath.read_text()

        resp = templates.TemplateResponse(request, "index.html", ctx)
        if not request.cookies.get("session_id"):
            resp.set_cookie("session_id", sid, max_age=86400 * 30)
        return resp
    finally:
        db.close()


@app.post("/generate")
async def generate(request: Request):
    sid = request.cookies.get("session_id") or uuid.uuid4().hex
    ip = request.client.host if request.client else "0.0.0.0"
    db = get_db()
    try:
        ok, msg = check_limits(db, sid, ip)
        if not ok:
            return RedirectResponse(url=f"/?error={quote(msg)}", status_code=303)

        next_ip = get_next_ip(db)
        if not next_ip:
            return RedirectResponse(url=f"/?error={quote('Semua IP habis!')}", status_code=303)

        priv, pub = gen_keys()
        conf = gen_conf(priv, next_ip)

        fname = f"wgfree_{next_ip.replace('.', '_')}.conf"
        fpath = CLIENTS_DIR / fname
        fpath.write_text(conf)

        try:
            add_peer(pub, next_ip)
        except Exception as e:
            if fpath.exists():
                fpath.unlink()
            return RedirectResponse(url=f"/?error={quote(f'Gagal: {e}')}", status_code=303)

        db.execute("INSERT INTO accounts (private_key, public_key, address, session_id, created_date) VALUES (?, ?, ?, ?, ?)",
            (priv, pub, next_ip, sid, date.today().isoformat()))
        increment_limits(db, sid, ip)
        db.commit()
    finally:
        db.close()

    resp = RedirectResponse(url=f"/?config={fname}", status_code=303)
    if not request.cookies.get("session_id"):
        resp.set_cookie("session_id", sid, max_age=86400 * 30)
    return resp


@app.get("/download/{fname}")
async def download(fname: str):
    fpath = CLIENTS_DIR / fname
    if not fpath.exists():
        raise HTTPException(404, "File not found")
    return FileResponse(str(fpath), filename=fname, media_type="application/octet-stream")


@app.get("/my", response_class=HTMLResponse)
async def my_configs(request: Request):
    sid = request.cookies.get("session_id")
    if not sid:
        return RedirectResponse(url="/", status_code=303)
    db = get_db()
    try:
        rows = db.execute(
            "SELECT id, address, created_at, created_date FROM accounts WHERE session_id = ? AND created_date = ? ORDER BY id DESC",
            (sid, date.today().isoformat())
        ).fetchall()
    finally:
        db.close()
    configs = []
    for r in rows:
        fname = f"wgfree_{r['address'].replace('.', '_')}.conf"
        fpath = CLIENTS_DIR / fname
        content = fpath.read_text() if fpath.exists() else ""
        configs.append({**dict(r), "config_content": content})
    today_str = date.today().strftime('%d %B %Y')
    return templates.TemplateResponse(request, "my_configs.html", {
        "configs": configs,
        "today_str": today_str,
    })


@app.get("/ssh", response_class=HTMLResponse)
async def ssh_page(request: Request):
    return templates.TemplateResponse(request, "ssh.html", {})


@app.get("/admin", response_class=HTMLResponse)
async def admin_page(request: Request):
    db = get_db()
    try:
        accounts = db.execute(
            "SELECT id, username, address, created_at FROM accounts ORDER BY id DESC LIMIT 100"
        ).fetchall()
        total = db.execute("SELECT COUNT(*) as c FROM accounts").fetchone()["c"]
        today = date.today().isoformat()
        row = db.execute("SELECT count FROM global_daily WHERE date = ?", (today,)).fetchone()
        daily = row["count"] if row else 0
    finally:
        db.close()
    return templates.TemplateResponse(request, "admin.html", {
        "accounts": accounts,
        "total": total,
        "daily": daily,
        "max_daily": MAX_DAILY,
    })


@app.on_event("startup")
def startup():
    init_db()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8007, reload=False)
