import asyncio
import uuid
import os
import subprocess
import pwd
import spwd
import crypt
import grp
import json
from pathlib import Path
import sqlite3
from datetime import datetime, timedelta
from fastapi import FastAPI, Form, Query, HTTPException, Body, UploadFile, File, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

sessions = {}
SESSION_EXPIRE_HOURS = 8760  # 1 year, effectively persistent

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "manage.db")

app = FastAPI(title="VPS Manager")
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")


@app.get("/")
async def root():
    return FileResponse(os.path.join(BASE_DIR, "static", "index.html"))


@app.get("/api/me")
async def me(token: str = ""):
    session = sessions.get(token)
    if not session or datetime.utcnow() > session["expires"]:
        return JSONResponse({"authenticated": False}, status_code=401)
    return {"authenticated": True, "username": session["username"]}


def check_sudo_access(username: str) -> bool:
    sudo_groups = ["sudo", "wheel", "admin"]
    try:
        pw = pwd.getpwnam(username)
        user_gid = pw.pw_gid
        try:
            user_groups = [g.gr_name for g in grp.getgrall() if username in g.gr_mem]
            grp_entry = grp.getgrgid(user_gid)
            if grp_entry:
                user_groups.append(grp_entry.gr_name)
        except Exception:
            user_groups = []
        for g in sudo_groups:
            if g in user_groups:
                return True
        result = subprocess.run(
            ["sudo", "-l", "-U", username],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0 and "may not" not in result.stdout.lower():
            return True
    except Exception:
        pass
    return False


def refresh_session(token):
    session = sessions.get(token)
    if session and datetime.utcnow() <= session["expires"]:
        session["expires"] = datetime.utcnow() + timedelta(hours=SESSION_EXPIRE_HOURS)
        return True
    return False


@app.post("/api/login")
async def login(username: str = Form(...), password: str = Form(...)):
    try:
        pwd.getpwnam(username)
        sp = spwd.getspnam(username)
        if crypt.crypt(password, sp.sp_pwdp) != sp.sp_pwdp:
            return JSONResponse(
                {"error": "Invalid username or password"}, status_code=401
            )
    except (KeyError, PermissionError):
        return JSONResponse(
            {"error": "Invalid username or password"}, status_code=401
        )
    if not check_sudo_access(username):
        return JSONResponse(
            {"error": "User does not have sudo access"}, status_code=403
        )
    token = str(uuid.uuid4())
    sessions[token] = {
        "username": username,
        "created": datetime.utcnow(),
        "expires": datetime.utcnow() + timedelta(hours=SESSION_EXPIRE_HOURS),
    }
    return {"token": token}


@app.get("/api/refresh")
async def api_refresh(token: str = Query(...)):
    session = sessions.get(token)
    if not session or datetime.utcnow() > session["expires"]:
        raise HTTPException(status_code=401, detail="Unauthorized")
    refresh_session(token)
    return {"ok": True}


def run_iptables(args: list[str]) -> str:
    try:
        result = subprocess.run(
            ["iptables"] + args,
            capture_output=True, text=True, timeout=10
        )
        if result.returncode != 0:
            return f"Error: {result.stderr.strip()}"
        return result.stdout
    except subprocess.TimeoutExpired:
        return "Error: Command timed out"
    except FileNotFoundError:
        return "Error: iptables not found"
    except Exception as e:
        return f"Error: {str(e)}"


@app.get("/api/iptables")
async def get_iptables(
    token: str = Query(...),
    table: str = Query("filter"),
    chain: str = Query("INPUT"),
):
    session = sessions.get(token)
    if not session or datetime.utcnow() > session["expires"]:
        raise HTTPException(status_code=401, detail="Unauthorized")
    if table not in ("filter", "nat", "mangle", "raw", "security"):
        raise HTTPException(status_code=400, detail="Invalid table")
    if chain.upper() not in ("INPUT", "OUTPUT", "FORWARD", "PREROUTING", "POSTROUTING"):
        raise HTTPException(status_code=400, detail="Invalid chain")
    output = run_iptables(["-t", table, "-L", chain.upper(), "-v", "-n", "--line-numbers"])
    return {"table": table, "chain": chain.upper(), "output": output}


def parse_iptables_rules(table: str, chain: str) -> list[dict]:
    output = run_iptables(["-t", table, "-L", chain, "-n", "-v", "--line-numbers"])
    if output.startswith("Error"):
        return []
    rules = []
    started = False
    for line in output.strip().split("\n"):
        s = line.strip()
        if not s:
            continue
        if s.startswith("Chain "):
            started = False
            continue
        if s.startswith("num "):
            started = True
            continue
        if started:
            parts = s.split(None, 10)
            if len(parts) >= 10:
                rules.append({
                    "num": int(parts[0]),
                    "pkts": parts[1],
                    "bytes": parts[2],
                    "target": parts[3],
                    "prot": parts[4],
                    "opt": parts[5],
                    "in": parts[6],
                    "out": parts[7],
                    "source": parts[8],
                    "destination": parts[9],
                    "extra": " ".join(parts[10:]) if len(parts) > 10 else "",
                })
    return rules


@app.get("/api/iptables/all")
async def get_all_iptables(token: str = Query(...)):
    session = sessions.get(token)
    if not session or datetime.utcnow() > session["expires"]:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return {
        "nat": {c: parse_iptables_rules("nat", c)
                for c in ["PREROUTING", "INPUT", "OUTPUT", "POSTROUTING"]},
        "filter": {c: parse_iptables_rules("filter", c)
                   for c in ["INPUT", "FORWARD", "OUTPUT"]},
    }


@app.get("/api/interfaces")
async def get_interfaces(token: str = Query(...)):
    session = sessions.get(token)
    if not session or datetime.utcnow() > session["expires"]:
        raise HTTPException(status_code=401, detail="Unauthorized")
    try:
        result = subprocess.run(
            ["ip", "-j", "a"], capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            import json
            data = json.loads(result.stdout)
            ifaces = [x["ifname"] for x in data if x.get("ifname") and x["ifname"] != "lo"]
        else:
            ifaces = []
            for line in result.stdout.split("\n"):
                import re
                m = re.match(r"^\d+:\s+(\S+):", line.strip())
                if m and m.group(1) != "lo":
                    ifaces.append(m.group(1))
        return {"interfaces": ifaces}
    except Exception as e:
        return {"interfaces": [], "error": str(e)}


@app.put("/api/iptables")
async def edit_iptables_rule(
    token: str = Form(...),
    table: str = Form(...),
    chain: str = Form(...),
    line: int = Form(...),
    rule: str = Form(...),
):
    session = sessions.get(token)
    if not session or datetime.utcnow() > session["expires"]:
        raise HTTPException(status_code=401, detail="Unauthorized")
    del_out = run_iptables(["-t", table, "-D", chain.upper(), str(line)])
    if del_out.startswith("Error"):
        return {"success": False, "error": del_out}
    add_out = run_iptables(["-t", table, "-I", chain.upper(), str(line)] + rule.split())
    if add_out.startswith("Error"):
        return {"success": False, "error": add_out}
    return {"success": True}


@app.post("/api/iptables")
async def add_iptables_rule(
    token: str = Form(...),
    table: str = Form("filter"),
    chain: str = Form(...),
    rule: str = Form(...),
    position: int = Form(0),
):
    session = sessions.get(token)
    if not session or datetime.utcnow() > session["expires"]:
        raise HTTPException(status_code=401, detail="Unauthorized")
    args = ["-t", table]
    if position > 0:
        args += ["-I", chain.upper(), str(position)]
    else:
        args += ["-A", chain.upper()]
    args += rule.split()
    output = run_iptables(args)
    if output.startswith("Error"):
        return {"success": False, "error": output}
    return {"success": True}


@app.delete("/api/iptables")
async def delete_iptables_rule(
    token: str = Query(...),
    table: str = Query("filter"),
    chain: str = Query(...),
    line: int = Query(...),
):
    session = sessions.get(token)
    if not session or datetime.utcnow() > session["expires"]:
        raise HTTPException(status_code=401, detail="Unauthorized")
    output = run_iptables(["-t", table, "-D", chain.upper(), str(line)])
    if output.startswith("Error"):
        return {"success": False, "error": output}
    return {"success": True}


@app.post("/api/iptables/flush")
async def flush_iptables_chain(
    token: str = Form(...),
    table: str = Form("filter"),
    chain: str = Form(...),
):
    session = sessions.get(token)
    if not session or datetime.utcnow() > session["expires"]:
        raise HTTPException(status_code=401, detail="Unauthorized")
    output = run_iptables(["-t", table, "-F", chain.upper()])
    if output.startswith("Error"):
        return {"success": False, "error": output}
    return {"success": True}


@app.get("/api/overview")
async def get_overview(token: str = Query(...)):
    session = sessions.get(token)
    if not session or datetime.utcnow() > session["expires"]:
        raise HTTPException(status_code=401, detail="Unauthorized")
    info = {}
    try:
        result = subprocess.run(["uptime"], capture_output=True, text=True, timeout=5)
        info["uptime"] = result.stdout.strip()
    except Exception:
        info["uptime"] = "N/A"
    try:
        result = subprocess.run(
            ["free", "-h"], capture_output=True, text=True, timeout=5
        )
        info["memory"] = result.stdout.strip()
    except Exception:
        info["memory"] = "N/A"
    try:
        result = subprocess.run(
            ["df", "-h", "--total"], capture_output=True, text=True, timeout=5
        )
        info["disk"] = result.stdout.strip()
    except Exception:
        info["disk"] = "N/A"
    try:
        result = subprocess.run(
            ["uname", "-a"], capture_output=True, text=True, timeout=5
        )
        info["kernel"] = result.stdout.strip()
    except Exception:
        info["kernel"] = "N/A"
    try:
        result = subprocess.run(
            ["hostnamectl"], capture_output=True, text=True, timeout=5
        )
        info["hostname"] = result.stdout.strip()
    except Exception:
        info["hostname"] = "N/A"
    try:
        result = subprocess.run(
            ["ps", "aux", "--sort=-%mem", "|", "head", "-11"],
            capture_output=True, text=True, timeout=5, shell=True
        )
        info["top_processes"] = result.stdout.strip()
    except Exception:
        info["top_processes"] = "N/A"
    return info


# ── Service Management ──────────────────────────────────────────────

def _init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("CREATE TABLE IF NOT EXISTS monitored (name TEXT PRIMARY KEY)")
    conn.commit()
    conn.close()

_init_db()


def load_monitored_services() -> list[str]:
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("SELECT name FROM monitored ORDER BY name").fetchall()
    conn.close()
    return [r[0] for r in rows]


def save_monitored_services(services: list[str]):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("DELETE FROM monitored")
    conn.executemany("INSERT INTO monitored (name) VALUES (?)", [(s,) for s in sorted(services)])
    conn.commit()
    conn.close()


def run_systemctl(args: list[str]) -> tuple[int, str, str]:
    result = subprocess.run(
        ["systemctl"] + args,
        capture_output=True, text=True, timeout=10
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def list_available_services() -> list[dict]:
    try:
        result = subprocess.run(
            ["systemctl", "list-unit-files", "--type=service", "--no-pager", "--no-legend", "--plain"],
            capture_output=True, text=True, timeout=10
        )
        services = []
        for line in result.stdout.strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) >= 2 and parts[0].endswith(".service"):
                services.append({
                    "name": parts[0],
                    "unit_file_state": parts[1],
                })
        return services
    except Exception:
        return []


def get_service_status(name: str) -> dict:
    _, active_state, _ = run_systemctl(["is-active", name])
    _, enabled_state, _ = run_systemctl(["is-enabled", name])
    _, sub_state, _ = run_systemctl(["show", name, "--property=SubState", "--value"])
    _, description, _ = run_systemctl(["show", name, "--property=Description", "--value"])
    return {
        "name": name,
        "active_state": active_state,
        "enabled_state": enabled_state,
        "sub_state": sub_state,
        "description": description,
    }


def get_service_memory(name: str) -> dict:
    try:
        _, cg_path, _ = run_systemctl(["show", name, "--property=ControlGroup", "--value"])
        cgroup_procs = f"/sys/fs/cgroup{cg_path}/cgroup.procs"
        try:
            with open(cgroup_procs) as f:
                pids = {int(line.strip()) for line in f if line.strip().isdigit()}
        except FileNotFoundError:
            pids = set()
        if not pids:
            _, main_pid_str, _ = run_systemctl(["show", name, "--property=MainPID", "--value"])
            main_pid = int(main_pid_str)
            if main_pid > 0:
                pids = {main_pid}
        if not pids:
            return {"rss_mb": 0, "pids": 0}
        total_rss = 0
        for pid in pids:
            try:
                with open(f"/proc/{pid}/status") as f:
                    for line in f:
                        if line.startswith("VmRSS:"):
                            total_rss += int(line.split()[1])
                            break
            except (FileNotFoundError, PermissionError, IndexError):
                pass
        return {"rss_mb": round(total_rss / 1024, 1), "pids": len(pids)}
    except Exception:
        return {"rss_mb": 0, "pids": 0}


@app.get("/api/services/available")
async def get_available_services(token: str = Query(...)):
    session = sessions.get(token)
    if not session or datetime.utcnow() > session["expires"]:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return {"services": list_available_services()}


@app.get("/api/services/monitored")
async def get_monitored(token: str = Query(...)):
    session = sessions.get(token)
    if not session or datetime.utcnow() > session["expires"]:
        raise HTTPException(status_code=401, detail="Unauthorized")
    names = load_monitored_services()
    statuses = []
    for n in names:
        svc = get_service_status(n)
        mem = get_service_memory(n)
        svc.update(mem)
        statuses.append(svc)
    return {"services": statuses}


@app.post("/api/services/monitored")
async def add_monitored(token: str = Body(..., embed=True), name: str = Body(..., embed=True)):
    session = sessions.get(token)
    if not session or datetime.utcnow() > session["expires"]:
        raise HTTPException(status_code=401, detail="Unauthorized")
    services = load_monitored_services()
    if name in services:
        return {"success": True, "message": "Already monitored"}
    services.append(name)
    save_monitored_services(services)
    return {"success": True}


@app.delete("/api/services/monitored")
async def remove_monitored(token: str = Query(...), name: str = Query(...)):
    session = sessions.get(token)
    if not session or datetime.utcnow() > session["expires"]:
        raise HTTPException(status_code=401, detail="Unauthorized")
    services = load_monitored_services()
    if name not in services:
        return {"success": True, "message": "Not monitored"}
    services.remove(name)
    save_monitored_services(services)
    return {"success": True}


@app.post("/api/services/{name}/start")
async def start_service(name: str, token: str = Query(...)):
    session = sessions.get(token)
    if not session or datetime.utcnow() > session["expires"]:
        raise HTTPException(status_code=401, detail="Unauthorized")
    code, out, err = run_systemctl(["start", name])
    return {"success": code == 0, "error": err if code != 0 else None}


@app.post("/api/services/{name}/stop")
async def stop_service(name: str, token: str = Query(...)):
    session = sessions.get(token)
    if not session or datetime.utcnow() > session["expires"]:
        raise HTTPException(status_code=401, detail="Unauthorized")
    code, out, err = run_systemctl(["stop", name])
    return {"success": code == 0, "error": err if code != 0 else None}


@app.post("/api/services/{name}/restart")
async def restart_service(name: str, token: str = Query(...)):
    session = sessions.get(token)
    if not session or datetime.utcnow() > session["expires"]:
        raise HTTPException(status_code=401, detail="Unauthorized")
    code, out, err = run_systemctl(["restart", name])
    return {"success": code == 0, "error": err if code != 0 else None}


@app.post("/api/services/{name}/enable")
async def enable_service(name: str, token: str = Query(...)):
    session = sessions.get(token)
    if not session or datetime.utcnow() > session["expires"]:
        raise HTTPException(status_code=401, detail="Unauthorized")
    code, out, err = run_systemctl(["enable", name])
    return {"success": code == 0, "error": err if code != 0 else None}


@app.get("/api/services/{name}/config")
async def get_service_config(name: str, token: str = Query(...)):
    session = sessions.get(token)
    if not session or datetime.utcnow() > session["expires"]:
        raise HTTPException(status_code=401, detail="Unauthorized")
    code, out, err = run_systemctl(["cat", name])
    if code != 0:
        code2, out2, _ = run_systemctl(["show", name, "--property=FragmentPath", "--value"])
        if code2 == 0 and out2:
            try:
                with open(out2, "r") as f:
                    return {"name": name, "config": f.read(), "source": out2}
            except Exception as e:
                return {"name": name, "config": "", "error": str(e)}
        return {"name": name, "config": "", "error": err or "Cannot read service config"}
    return {"name": name, "config": out, "source": "systemctl cat"}


@app.post("/api/services/{name}/disable")
async def disable_service(name: str, token: str = Query(...)):
    session = sessions.get(token)
    if not session or datetime.utcnow() > session["expires"]:
        raise HTTPException(status_code=401, detail="Unauthorized")
    code, out, err = run_systemctl(["disable", name])
    return {"success": code == 0, "error": err if code != 0 else None}


@app.get("/api/services/{name}/logs")
async def get_service_logs(name: str, token: str = Query(...)):
    session = sessions.get(token)
    if not session or datetime.utcnow() > session["expires"]:
        raise HTTPException(status_code=401, detail="Unauthorized")
    try:
        result = subprocess.run(
            ["journalctl", "-u", name, "-n", "20", "--no-pager", "-o", "short"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode != 0:
            return {"success": False, "error": result.stderr.strip(), "logs": []}
        logs = [l for l in result.stdout.strip().split("\n") if l]
        return {"success": True, "logs": logs[-20:]}
    except Exception as e:
        return {"success": False, "error": str(e), "logs": []}


# ── Docker Management ──────────────────────────────────────────────

def run_docker(args: list[str], timeout: int = 15) -> tuple[int, str, str]:
    try:
        result = subprocess.run(
            ["docker"] + args,
            capture_output=True, text=True, timeout=timeout
        )
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except subprocess.TimeoutExpired:
        return 1, "", "Command timed out"
    except FileNotFoundError:
        return 1, "", "docker not found"
    except Exception as e:
        return 1, "", str(e)


def get_docker_stats() -> dict:
    code, out, _ = run_docker(["stats", "--no-stream", "--format", "{{.Name}}\t{{.MemUsage}}\t{{.MemPerc}}\t{{.CPUPerc}}"])
    stats = {}
    if code == 0 and out:
        for line in out.split("\n"):
            parts = line.split("\t")
            if len(parts) >= 4:
                name = parts[0].strip()
                stats[name] = {
                    "mem_usage": parts[1].strip(),
                    "mem_perc": parts[2].strip(),
                    "cpu_perc": parts[3].strip(),
                }
    return stats


@app.get("/api/docker/containers")
async def list_docker_containers(token: str = Query(...)):
    session = sessions.get(token)
    if not session or datetime.utcnow() > session["expires"]:
        raise HTTPException(status_code=401, detail="Unauthorized")
    code, out, err = run_docker(["ps", "-a", "--format", "{{.ID}}\t{{.Names}}\t{{.Image}}\t{{.Status}}\t{{.State}}\t{{.Ports}}"])
    if code != 0:
        raise HTTPException(status_code=500, detail=err or "Failed to list containers")
    containers = []
    for line in out.split("\n"):
        parts = line.split("\t")
        if len(parts) < 5:
            continue
        containers.append({
            "id": parts[0].strip(),
            "name": parts[1].strip(),
            "image": parts[2].strip(),
            "status": parts[3].strip(),
            "state": parts[4].strip(),
            "ports": parts[5].strip() if len(parts) > 5 else "",
        })
    stats = get_docker_stats()
    for c in containers:
        s = stats.get(c["name"], {})
        c["mem_usage"] = s.get("mem_usage", "")
        c["mem_perc"] = s.get("mem_perc", "")
        c["cpu_perc"] = s.get("cpu_perc", "")
    return {"containers": containers}


@app.get("/api/docker/containers/{name}/inspect")
async def inspect_docker_container(name: str, token: str = Query(...)):
    session = sessions.get(token)
    if not session or datetime.utcnow() > session["expires"]:
        raise HTTPException(status_code=401, detail="Unauthorized")
    code, out, err = run_docker(["inspect", name])
    if code != 0:
        raise HTTPException(status_code=500, detail=err or "Failed to inspect container")
    try:
        data = json.loads(out)
        if isinstance(data, list) and len(data) > 0:
            data = data[0]
        return {"name": name, "config": json.dumps(data, indent=2)}
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Failed to parse inspect output")


@app.post("/api/docker/containers/{name}/start")
async def start_docker_container(name: str, token: str = Query(...)):
    session = sessions.get(token)
    if not session or datetime.utcnow() > session["expires"]:
        raise HTTPException(status_code=401, detail="Unauthorized")
    code, out, err = run_docker(["start", name])
    return {"success": code == 0, "error": err if code != 0 else None}


@app.post("/api/docker/containers/{name}/stop")
async def stop_docker_container(name: str, token: str = Query(...)):
    session = sessions.get(token)
    if not session or datetime.utcnow() > session["expires"]:
        raise HTTPException(status_code=401, detail="Unauthorized")
    code, out, err = run_docker(["stop", name])
    return {"success": code == 0, "error": err if code != 0 else None}


# ── File Explorer ────────────────────────────────────────────────

def _is_binary(data: bytes) -> bool:
    return b'\x00' in data[:8192]


@app.get("/api/explorer")
async def explorer(
    token: str = Query(...),
    path: str = Query("/"),
):
    session = sessions.get(token)
    if not session or datetime.utcnow() > session["expires"]:
        raise HTTPException(status_code=401, detail="Unauthorized")

    # Restrict to safe paths
    real_path = os.path.realpath(path)
    allowed = [os.path.realpath(p) for p in ["/", "/home", "/etc", "/var/log", "/tmp", "/root"]]
    if not any(real_path.startswith(a + "/") or real_path == a for a in allowed):
        raise HTTPException(status_code=403, detail="Access denied")

    try:
        entries = []
        for name in sorted(os.listdir(real_path)):
            full = os.path.join(real_path, name)
            try:
                st = os.lstat(full)
            except OSError:
                continue
            import stat as sm
            is_dir = sm.S_ISDIR(st.st_mode)
            entries.append({
                "name": name,
                "path": full.replace(os.sep, "/"),
                "is_dir": is_dir,
                "size": st.st_size if not is_dir else None,
                "mtime": st.st_mtime,
            })

        # Sort: directories first, then files
        entries.sort(key=lambda e: (not e["is_dir"], e["name"].lower()))

        return {"path": real_path.replace(os.sep, "/"), "entries": entries}
    except PermissionError:
        raise HTTPException(status_code=403, detail="Permission denied")
    except OSError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/explorer/read")
async def explorer_read(
    token: str = Query(...),
    path: str = Query(...),
):
    session = sessions.get(token)
    if not session or datetime.utcnow() > session["expires"]:
        raise HTTPException(status_code=401, detail="Unauthorized")

    real_path = os.path.realpath(path)
    allowed = [os.path.realpath(p) for p in ["/", "/home", "/etc", "/var/log", "/tmp", "/root"]]
    if not any(real_path.startswith(a + "/") or real_path == a for a in allowed):
        raise HTTPException(status_code=403, detail="Access denied")

    try:
        with open(real_path, "rb") as f:
            data = f.read(1 * 1024 * 1024)  # max 1MB
    except OSError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if _is_binary(data):
        return {"path": real_path.replace(os.sep, "/"), "type": "binary", "size": len(data)}

    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        try:
            text = data.decode("latin-1")
        except Exception:
            return {"path": real_path.replace(os.sep, "/"), "type": "binary", "size": len(data)}

    return {"path": real_path.replace(os.sep, "/"), "type": "text", "content": text}


@app.get("/api/explorer/image")
async def explorer_image(
    token: str = Query(...),
    path: str = Query(...),
):
    session = sessions.get(token)
    if not session or datetime.utcnow() > session["expires"]:
        raise HTTPException(status_code=401, detail="Unauthorized")

    real_path = os.path.realpath(path)
    allowed = [os.path.realpath(p) for p in ["/", "/home", "/etc", "/var/log", "/tmp", "/root"]]
    if not any(real_path.startswith(a + "/") or real_path == a for a in allowed):
        raise HTTPException(status_code=403, detail="Access denied")

    try:
        with open(real_path, "rb") as f:
            data = f.read()
    except OSError as e:
        raise HTTPException(status_code=400, detail=str(e))

    import mimetypes
    mime, _ = mimetypes.guess_type(path)
    if not mime or not mime.startswith("image/"):
        return {"path": real_path.replace(os.sep, "/"), "type": "binary", "size": len(data)}

    import base64
    b64 = base64.b64encode(data).decode()
    ext = mime.split("/")[1]
    return {
        "path": real_path.replace(os.sep, "/"),
        "type": "image",
        "mime": mime,
        "data_url": f"data:{mime};base64,{b64}",
    }


@app.post("/api/explorer/write")
async def explorer_write(
    token: str = Query(...),
    path: str = Body(...),
    content: str = Body(...),
):
    session = sessions.get(token)
    if not session or datetime.utcnow() > session["expires"]:
        raise HTTPException(status_code=401, detail="Unauthorized")

    real_path = os.path.realpath(path)
    allowed = [os.path.realpath(p) for p in ["/", "/home", "/etc", "/var/log", "/tmp", "/root"]]
    if not any(real_path.startswith(a + "/") or real_path == a for a in allowed):
        raise HTTPException(status_code=403, detail="Access denied")

    try:
        with open(real_path, "w") as f:
            f.write(content)
        return {"success": True}
    except PermissionError:
        raise HTTPException(status_code=403, detail="Permission denied")
    except OSError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/api/explorer/delete")
async def explorer_delete(
    token: str = Query(...),
    path: str = Query(...),
):
    session = sessions.get(token)
    if not session or datetime.utcnow() > session["expires"]:
        raise HTTPException(status_code=401, detail="Unauthorized")

    real_path = os.path.realpath(path)
    allowed = [os.path.realpath(p) for p in ["/", "/home", "/etc", "/var/log", "/tmp", "/root"]]
    if not any(real_path.startswith(a + "/") or real_path == a for a in allowed):
        raise HTTPException(status_code=403, detail="Access denied")

    import shutil
    try:
        if os.path.isdir(real_path):
            shutil.rmtree(real_path)
        else:
            os.remove(real_path)
        return {"success": True}
    except PermissionError:
        raise HTTPException(status_code=403, detail="Permission denied")
    except OSError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/explorer/upload")
async def explorer_upload(
    token: str = Query(...),
    path: str = Body(..., embed=True),
    file: UploadFile = File(...),
    new_name: str = Body(None, embed=True),
):
    session = sessions.get(token)
    if not session or datetime.utcnow() > session["expires"]:
        raise HTTPException(status_code=401, detail="Unauthorized")

    real_path = os.path.realpath(path)
    allowed = [os.path.realpath(p) for p in ["/", "/home", "/etc", "/var/log", "/tmp", "/root"]]
    if not any(real_path.startswith(a + "/") or real_path == a for a in allowed):
        raise HTTPException(status_code=403, detail="Access denied")

    filename = new_name or file.filename
    dest = os.path.join(real_path, filename)
    real_dest = os.path.realpath(dest)
    if not any(real_dest.startswith(a + "/") or real_dest == a for a in allowed):
        raise HTTPException(status_code=403, detail="Access denied")

    try:
        with open(dest, "wb") as f:
            content = await file.read()
            f.write(content)
        return {"success": True, "path": real_dest.replace(os.sep, "/"), "size": len(content)}
    except PermissionError:
        raise HTTPException(status_code=403, detail="Permission denied")
    except OSError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.api_route("/", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
@app.api_route("/explorer{rest:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def catch_all(request: Request, rest: str = "/"):
    if rest and rest != "/":
        return RedirectResponse(url="/#/explorer/" + rest.lstrip("/"), status_code=307)
    return FileResponse("static/index.html")
