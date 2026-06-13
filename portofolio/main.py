import json
import os
from pathlib import Path

from fastapi import FastAPI, Request, Response, Cookie, HTTPException
from fastapi.responses import RedirectResponse
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

@app.get("/set-language/{lang}")
async def set_language(lang: str, request: Request, next: str = "/"):
    if lang not in ("en", "id"):
        raise HTTPException(status_code=400, detail="Invalid language")
    response = RedirectResponse(url=next)
    response.set_cookie(key="lang", value=lang)
    return response
