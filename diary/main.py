import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import text as sa_text

from database import engine, Base
from models import User
from auth import hash_password
from routes.auth_route import router as auth_router
from routes.posts_route import router as posts_router
from routes.comments_route import router as comments_router
from routes.reacts_route import router as reacts_router
from routes.admin_route import router as admin_router
from routes.notifications_route import router as notifications_router

REQUIRED_ENV = ["DB_USER", "DB_PASS", "DB_NAME", "ADMIN_USER", "ADMIN_PASS", "SECRET_KEY"]
for key in REQUIRED_ENV:
    if not os.getenv(key):
        print(f"ERROR: {key} tidak ditemukan di .env", file=sys.stderr)
        sys.exit(1)

app = FastAPI()

app.mount("/assets", StaticFiles(directory="/home/mamad/diary/assets"), name="assets")
app.mount("/static", StaticFiles(directory="/home/mamad/diary/static"), name="static")

templates = Jinja2Templates(directory="/home/mamad/diary/templates")

app.include_router(auth_router)
app.include_router(posts_router)
app.include_router(comments_router)
app.include_router(reacts_router)
app.include_router(admin_router)
app.include_router(notifications_router)


@app.on_event("startup")
async def startup():
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    except Exception as e:
        print(f"ERROR: Gagal koneksi ke database — {e}", file=sys.stderr)
        sys.exit(1)

    async with engine.begin() as conn:
        result = await conn.execute(
            sa_text("SELECT COUNT(*) FROM users WHERE role = 'admin'")
        )
        count = result.scalar()
        if count == 0:
            admin_username = os.getenv("ADMIN_USER", "admin")
            admin_password = os.getenv("ADMIN_PASS", "admin")
            await conn.execute(
                sa_text(
                    "INSERT INTO users (username, password_hash, role, approved, profile_pic) "
                    "VALUES (:u, :p, 'admin', TRUE, :pic) ON CONFLICT (username) DO NOTHING"
                ),
                {"u": admin_username, "p": hash_password(admin_password), "pic": "/assets/default-profile.png"},
            )
            print(f"Admin user '{admin_username}' created.")

        await conn.execute(
            sa_text("UPDATE users SET profile_pic = :pic WHERE profile_pic IS NULL"),
            {"pic": "/assets/default-profile.png"},
        )


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})


@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    return templates.TemplateResponse("settings.html", {"request": request})


@app.get("/roles", response_class=HTMLResponse)
async def roles_page(request: Request):
    return templates.TemplateResponse("roles.html", {"request": request})


@app.get("/admin", response_class=HTMLResponse)
async def admin_page(request: Request):
    return templates.TemplateResponse("admin.html", {"request": request})
