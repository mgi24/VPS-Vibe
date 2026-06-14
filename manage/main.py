import asyncio
import uuid
import os
import subprocess
import pwd
import spwd
import crypt
import grp
from datetime import datetime, timedelta
from fastapi import FastAPI, Form, Query, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

sessions = {}
SESSION_EXPIRE_HOURS = 24

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

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


@app.get("/api/iptables/chains")
async def get_iptables_chains(token: str = Query(...), table: str = Query("filter")):
    session = sessions.get(token)
    if not session or datetime.utcnow() > session["expires"]:
        raise HTTPException(status_code=401, detail="Unauthorized")
    if table not in ("filter", "nat", "mangle", "raw", "security"):
        raise HTTPException(status_code=400, detail="Invalid table")
    output = run_iptables(["-t", table, "-L", "-v", "-n", "--line-numbers"])
    return {"table": table, "output": output}


@app.get("/api/iptables/tables")
async def get_iptables_tables(token: str = Query(...)):
    session = sessions.get(token)
    if not session or datetime.utcnow() > session["expires"]:
        raise HTTPException(status_code=401, detail="Unauthorized")
    tables = []
    for t in ("filter", "nat", "mangle", "raw", "security"):
        try:
            out = run_iptables(["-t", t, "-L", "-v", "-n", "--line-numbers"])
            if not out.startswith("Error"):
                tables.append({"name": t, "has_rules": bool(out.strip())})
        except Exception:
            pass
    return {"tables": tables}


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
