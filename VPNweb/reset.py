#!/usr/bin/env python3
import os, sqlite3

DB = "/opt/wireguardfree/data.db"

if os.geteuid() != 0:
    print("Jalankan sebagai root: sudo python3 reset.py")
    exit(1)

db = sqlite3.connect(DB)
db.execute("DELETE FROM rate_limits")
db.execute("DELETE FROM global_daily")
db.commit()
db.close()
print("OK — rate limit session & daily di-reset. User bisa register lagi.")
