import asyncio
import os
import secrets
import time
from pathlib import Path

import mysql.connector
import uvicorn
from fastapi import FastAPI, File, Query, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

BASE_DIR = Path(__file__).parent
DL_FILE = Path("/var/www/cftest/dl-chunk.bin")

DB_CONFIG = {
    "host": "localhost",
    "user": "cftest",
    "password": "cftest123",
    "database": "cftest",
}

if not DL_FILE.exists():
    DL_FILE.write_bytes(secrets.token_bytes(5 * 1024 * 1024))

app = FastAPI()
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

def get_db():
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    cursor.execute("SET time_zone = '+00:00'")
    cursor.close()
    return conn

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(request, "index.html", {})

@app.get("/api/ping")
async def ping():
    return {"time": time.time()}

@app.get("/api/download-stream")
async def download_stream():
    return Response(
        headers={
            "X-Accel-Redirect": "/internal/dl-chunk.bin",
            "Cache-Control": "no-store",
        }
    )

@app.post("/api/upload")
async def upload(file: UploadFile = File(...)):
    total = 0
    try:
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            total += len(chunk)
    except asyncio.CancelledError:
        pass
    return {"size_bytes": total}

@app.post("/api/log-throughput")
async def log_throughput(data: dict):
    session_id = data.get("session_id")
    entries = data.get("entries", [])
    conn = get_db()
    cursor = conn.cursor()
    try:
        for e in entries:
            cursor.execute(
                "INSERT INTO test_results (session_id, test_type, value_ms, throughput_mbps, data_size_bytes, duration_ms) VALUES (%s, %s, %s, %s, %s, %s)",
                (
                    session_id,
                    e["test_type"],
                    e.get("value_ms"),
                    e.get("throughput_mbps"),
                    e.get("data_size_bytes"),
                    e.get("duration_ms"),
                ),
            )
        conn.commit()
    finally:
        cursor.close()
        conn.close()
    return {"status": "ok"}

@app.get("/api/reports")
async def reports(
    since: str | None = Query(None),
    until: str | None = Query(None),
    test_type: str | None = Query(None),
    session_id: str | None = Query(None),
):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        where = []
        params = []
        if since:
            where.append("created_at >= %s")
            params.append(since)
        if until:
            where.append("created_at <= %s")
            params.append(until)
        if test_type:
            where.append("test_type = %s")
            params.append(test_type)
        if session_id:
            where.append("session_id = %s")
            params.append(session_id)
        where_clause = " AND ".join(where) if where else "1=1"
        cursor.execute(
            f"SELECT id, session_id, test_type, value_ms, throughput_mbps, data_size_bytes, duration_ms, created_at FROM test_results WHERE {where_clause} ORDER BY created_at ASC",
            params,
        )
        rows = cursor.fetchall()
        for r in rows:
            r["created_at"] = r["created_at"].isoformat() + "Z"
        return JSONResponse(rows)
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8010, log_level="info")
