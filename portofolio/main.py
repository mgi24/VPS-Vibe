import json
import os
import time
from pathlib import Path

from fastapi import FastAPI, Request, Response, Cookie, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app = FastAPI()

BASE_DIR = Path(__file__).parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "assets")), name="static")

def load_content(lang: str) -> dict:
    file_path = BASE_DIR / "content" / f"{lang}.json"
    if not file_path.exists():
        file_path = BASE_DIR / "content" / "en.json"
    with open(file_path, "r") as f:
        return json.load(f)

# --- Resource monitoring ---

_prev_cpu = None

def _read_cpu():
    with open("/proc/stat") as f:
        parts = f.readline().split()
    vals = [int(v) for v in parts[1:]]
    idle = vals[3] + vals[4]
    total = sum(vals)
    return total, idle

def _read_ram():
    mem = {}
    with open("/proc/meminfo") as f:
        for line in f:
            parts = line.split()
            key = parts[0].rstrip(":")
            if key in ("MemTotal", "MemAvailable"):
                mem[key] = int(parts[1])  # kB
    return mem

@app.get("/resource")
async def get_resource(request: Request):
    global _prev_cpu

    total, idle = _read_cpu()

    cpu = 0.0
    if _prev_cpu is not None:
        td = total - _prev_cpu[0]
        id = idle - _prev_cpu[1]
        if td > 0:
            cpu = round((td - id) / td * 100, 1)
    _prev_cpu = (total, idle)

    ram = _read_ram()
    total_kb = ram.get("MemTotal", 0)
    avail_kb = ram.get("MemAvailable", 0)
    used_kb = total_kb - avail_kb
    ram_pct = round(used_kb / total_kb * 100, 1) if total_kb > 0 else 0

    return {
        "cpu": cpu,
        "ram_percent": ram_pct,
        "ram_used_gb": round(used_kb / 1_048_576, 1),
        "ram_total_gb": round(total_kb / 1_048_576, 1),
        "cores": 4,
        "arch": "arm64",
    }

# --- Pages ---

@app.get("/")
async def index(request: Request, lang: str = Cookie(default="en")):
    content = load_content(lang)
    return templates.TemplateResponse(request, "index.html", {"content": content, "lang": lang})

@app.get("/demo")
async def demo(request: Request, lang: str = Cookie(default="en")):
    content = load_content(lang)
    return templates.TemplateResponse(request, "demo.html", {"content": content, "lang": lang})

@app.get("/contact")
async def contact(request: Request, lang: str = Cookie(default="en")):
    content = load_content(lang)
    return templates.TemplateResponse(request, "contact.html", {"content": content, "lang": lang})

@app.get("/phone")
async def phone(request: Request, lang: str = Cookie(default="en")):
    content = load_content(lang)
    return templates.TemplateResponse(request, "phone.html", {"content": content, "lang": lang})

@app.get("/set-language/{lang}")
async def set_language(lang: str, request: Request, next: str = "/"):
    if lang not in ("en", "id"):
        raise HTTPException(status_code=400, detail="Invalid language")
    response = RedirectResponse(url=next)
    response.set_cookie(key="lang", value=lang)
    return response
