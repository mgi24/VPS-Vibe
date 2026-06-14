import asyncio
import uuid
import os
import pty
import fcntl
import struct
import termios
import signal
import pwd
import spwd
import crypt
from datetime import datetime, timedelta
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Form
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

sessions = {}
SESSION_EXPIRE_HOURS = 24

app = FastAPI(title="WebSSH")
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def root():
    return FileResponse("static/index.html")


@app.get("/api/me")
async def me(token: str = ""):
    session = sessions.get(token)
    if not session or datetime.utcnow() > session["expires"]:
        return JSONResponse({"authenticated": False}, status_code=401)
    return {"authenticated": True, "username": session["username"]}


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
    token = str(uuid.uuid4())
    sessions[token] = {
        "username": username,
        "created": datetime.utcnow(),
        "expires": datetime.utcnow() + timedelta(hours=SESSION_EXPIRE_HOURS),
    }
    return {"token": token}


async def bash_loop(websocket: WebSocket, username: str, term_size=(24, 80)):
    master_fd = None
    child_pid = None
    try:
        pw = pwd.getpwnam(username)
        master_fd, slave_fd = pty.openpty()
        buf = struct.pack('HHHH', term_size[0], term_size[1], 0, 0)
        fcntl.ioctl(master_fd, termios.TIOCSWINSZ, buf)
        os.set_blocking(master_fd, False)
        child_pid = os.fork()

        if child_pid == 0:
            os.close(master_fd)
            slave_name = os.ttyname(slave_fd)
            os.setsid()
            ctty = os.open(slave_name, os.O_RDWR)
            os.dup2(ctty, 0)
            os.dup2(ctty, 1)
            os.dup2(ctty, 2)
            if ctty > 2:
                os.close(ctty)
            if slave_fd > 2:
                os.close(slave_fd)
            os.setgid(pw.pw_gid)
            os.setuid(pw.pw_uid)
            pty_env = os.environ.copy()
            pty_env["TERM"] = "xterm-256color"
            pty_env["HOME"] = pw.pw_dir
            pty_env["USER"] = username
            pty_env["LOGNAME"] = username
            pty_env["SHELL"] = pw.pw_shell
            os.chdir(pw.pw_dir)
            os.execve(pw.pw_shell, ["-" + os.path.basename(pw.pw_shell), "-i"], pty_env)
            os._exit(1)
        os.close(slave_fd)

        loop = asyncio.get_running_loop()
        pty_read_ready = None

        def on_pty_readable():
            nonlocal pty_read_ready
            if pty_read_ready is not None and not pty_read_ready.done():
                pty_read_ready.set_result(None)

        loop.add_reader(master_fd, on_pty_readable)

        async def read_pty():
            nonlocal pty_read_ready
            try:
                while True:
                    pty_read_ready = loop.create_future()
                    await pty_read_ready
                    while True:
                        try:
                            data = os.read(master_fd, 65536)
                            if not data:
                                return
                            await websocket.send_json({"type": "data", "data": data.decode("utf-8", errors="replace")})
                        except BlockingIOError:
                            break
            except Exception:
                pass

        async def write_pty():
            try:
                while True:
                    msg = await websocket.receive_json()
                    t = msg.get("type")
                    if t == "data":
                        data = msg["data"].encode("utf-8")
                        offset = 0
                        while offset < len(data):
                            try:
                                written = os.write(master_fd, data[offset:])
                                offset += written
                            except BlockingIOError:
                                await asyncio.sleep(0.005)
                    elif t == "resize":
                        try:
                            buf = struct.pack('HHHH', msg["rows"], msg["cols"], 0, 0)
                            fcntl.ioctl(master_fd, termios.TIOCSWINSZ, buf)
                        except Exception:
                            pass
                    elif t == "close":
                        break
            except Exception:
                pass

        reader = asyncio.create_task(read_pty())
        writer = asyncio.create_task(write_pty())
        done, pending = await asyncio.wait(
            [reader, writer], return_when=asyncio.FIRST_COMPLETED
        )
        for task in pending:
            task.cancel()
        for task in pending:
            try:
                await task
            except (asyncio.CancelledError, Exception):
                pass

    except Exception as e:
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass
    finally:
        try:
            loop.remove_reader(master_fd)
        except Exception:
            pass
        if child_pid and child_pid > 0:
            try:
                os.kill(child_pid, signal.SIGKILL)
                os.waitpid(child_pid, 0)
            except Exception:
                pass
        if master_fd is not None:
            try:
                os.close(master_fd)
            except Exception:
                pass
        try:
            await websocket.close()
        except Exception:
            pass


@app.websocket("/ws")
async def ws(websocket: WebSocket):
    token = websocket.query_params.get("token")
    if not token or token not in sessions:
        await websocket.close(code=4001, reason="Unauthorized")
        return
    sessions[token]["expires"] = datetime.utcnow() + timedelta(
        hours=SESSION_EXPIRE_HOURS
    )

    await websocket.accept()
    try:
        msg = await websocket.receive_json()
        if msg.get("type") != "start":
            await websocket.send_json(
                {"type": "error", "message": "First message must be 'start'"}
            )
            return
        initial_size = (msg.get("rows", 24), msg.get("cols", 80))
        username = sessions[token]["username"]
        await bash_loop(websocket, username, initial_size)
    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass
