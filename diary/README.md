# MMV Diary

A dark-mode social media web app built with FastAPI + PostgreSQL. Facebook-style feed, comments, reacts, notifications, and role-based access.

## Features

- **Posts** — text, image, video with drag-drop/paste upload, segment tags
- **Comments & Reacts** — logged-in users + anonymous guests
- **Roles** — admin, poster, general; admin manages roles via panel
- **Notifications** — unread badge, mark read, read-all
- **Image Editor** — rotate 90°, crop with draggable handles
- **Three-dot menu** — edit/delete own posts (admins edit/delete any)

## Tech

- **Backend:** FastAPI + SQLAlchemy (async) + PostgreSQL
- **Auth:** JWT (access + refresh tokens), pbkdf2_sha256
- **Frontend:** Jinja2 templates, vanilla JS, dark theme CSS

## Setup

```bash
cd diary
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # edit database URL + secrets
python main.py
```

## Environment

Create `.env` with:
```
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/dbname
SECRET_KEY=random-secret
ADMIN_USERNAME=admin
ADMIN_PASSWORD=securepass
```

## Nginx

The app runs on port 8007 behind nginx at `debug.misbahwork.my.id`. Example config in `/etc/nginx/sites-enabled/debug.misbahwork.my.id`.

## License

MIT
