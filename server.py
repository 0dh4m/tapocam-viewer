import os
import sys
import json
import time
import hmac
import hashlib
import asyncio
import secrets
import socket
import subprocess
from pathlib import Path
import aiohttp
from aiohttp import web
import ptz

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
CONFIG_FILE = BASE_DIR / "config.json"
GO2RTC_YAML = BASE_DIR / "go2rtc.yaml"
GO2RTC_EXE = BASE_DIR / "go2rtc.exe"

SECRET_KEY = secrets.token_bytes(32)

failed_attempts = {}

go2rtc_process = None

privacy_mode_active = False

def load_config():
    if not CONFIG_FILE.exists():
        default_cfg = {
            "camera": {"ip": "", "username": "", "password": "", "rtsp_port": 554, "stream_hd": "stream1", "stream_sd": "stream2"},
            "security": {"pin": "1234", "pin_set": False, "session_timeout_minutes": 1440, "max_failed_attempts": 5, "lockout_minutes": 5},
            "server": {"host": "0.0.0.0", "port": 5000}
        }
        save_config(default_cfg)
        return default_cfg
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_config(cfg):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)

import urllib.parse

def generate_go2rtc_yaml(cfg):
    cam = cfg.get("camera", {})
    ip = cam.get("ip", "").strip()
    user = cam.get("username", "").strip()
    pwd = cam.get("password", "").strip()
    port = cam.get("rtsp_port", 554)
    hd = cam.get("stream_hd", "stream1")
    sd = cam.get("stream_sd", "stream2")

    content = "api:\n  listen: \"127.0.0.1:1984\"\n\nwebrtc:\n  listen: \":8555\"\n\n"
    
    if ip and user and pwd:
        safe_user = urllib.parse.quote(user, safe='')
        safe_pwd = urllib.parse.quote(pwd, safe='')
        hd_url = f"rtsp://{safe_user}:{safe_pwd}@{ip}:{port}/{hd}"
        sd_url = f"rtsp://{safe_user}:{safe_pwd}@{ip}:{port}/{sd}"
        content += f"streams:\n  tapo_hd:\n    - {hd_url}\n  tapo_sd:\n    - {sd_url}\n"
    else:
        content += "streams: {}\n"

    with open(GO2RTC_YAML, "w", encoding="utf-8") as f:
        f.write(content)

def restart_go2rtc():
    global go2rtc_process
    if go2rtc_process and go2rtc_process.poll() is None:
        try:
            go2rtc_process.terminate()
            go2rtc_process.wait(timeout=3)
        except Exception:
            try:
                go2rtc_process.kill()
            except Exception:
                pass
    
    if GO2RTC_EXE.exists():
        cfg = load_config()
        generate_go2rtc_yaml(cfg)
        startupinfo = None
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        
        go2rtc_process = subprocess.Popen(
            [str(GO2RTC_EXE), "-config", str(GO2RTC_YAML)],
            cwd=str(BASE_DIR),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            startupinfo=startupinfo
        )

def make_session_token(expiry_timestamp):
    payload = f"session:{expiry_timestamp}".encode('utf-8')
    sig = hmac.new(SECRET_KEY, payload, hashlib.sha256).hexdigest()
    return f"{expiry_timestamp}:{sig}"

def verify_session_token(token):
    if not token or ":" not in token:
        return False
    try:
        exp_str, sig = token.split(":", 1)
        expiry = float(exp_str)
        if time.time() > expiry:
            return False
        expected_sig = hmac.new(SECRET_KEY, f"session:{exp_str}".encode('utf-8'), hashlib.sha256).hexdigest()
        return hmac.compare_digest(sig, expected_sig)
    except Exception:
        return False

def is_authenticated(request):
    cookie = request.cookies.get("tapo_session")
    return verify_session_token(cookie)

def get_client_ip(request):
    return request.headers.get("X-Forwarded-For", request.remote or "unknown")

# --- Routes ---

async def handle_index(request):
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return web.FileResponse(index_path)
    return web.Response(text="Dashboard loading...", content_type="text/html")

async def api_auth_check(request):
    cfg = load_config()
    pin_set = cfg.get("security", {}).get("pin_set", False)
    auth = is_authenticated(request)
    cam = cfg.get("camera", {})
    cam_configured = bool(cam.get("ip") and cam.get("username") and cam.get("password"))
    
    return web.json_response({
        "authenticated": auth,
        "pin_set": pin_set,
        "camera_configured": cam_configured,
        "camera_ip": cam.get("ip", ""),
        "privacy_active": privacy_mode_active
    })

async def api_auth_login(request):
    ip = get_client_ip(request)
    now = time.time()

    cfg = load_config()
    sec = cfg.get("security", {})
    max_attempts = sec.get("max_failed_attempts", 5)
    lockout_secs = sec.get("lockout_minutes", 5) * 60

    if ip in failed_attempts:
        attempts, lock_time = failed_attempts[ip]
        if attempts >= max_attempts:
            remaining = int(lockout_secs - (now - lock_time))
            if remaining > 0:
                return web.json_response({
                    "success": False,
                    "error": f"Too many failed attempts. Locked out for {remaining} seconds."
                }, status=429)
            else:
                del failed_attempts[ip]

    try:
        data = await request.json()
        input_pin = str(data.get("pin", "")).strip()
    except Exception:
        return web.json_response({"success": False, "error": "Invalid request format"}, status=400)

    actual_pin = str(sec.get("pin", "1234")).strip()

    if hmac.compare_digest(input_pin, actual_pin):
        if ip in failed_attempts:
            del failed_attempts[ip]
        
        timeout_minutes = sec.get("session_timeout_minutes", 1440)
        expiry = now + (timeout_minutes * 60)
        token = make_session_token(expiry)

        resp = web.json_response({"success": True})
        resp.set_cookie("tapo_session", token, max_age=int(timeout_minutes * 60), httponly=True, samesite="Lax")
        return resp
    else:
        attempts, _ = failed_attempts.get(ip, (0, now))
        attempts += 1
        failed_attempts[ip] = (attempts, now)
        remaining = max_attempts - attempts
        return web.json_response({
            "success": False,
            "error": "Incorrect PIN" if remaining > 0 else f"Too many attempts. Locked for {sec.get('lockout_minutes', 5)} minutes.",
            "attempts_remaining": max(0, remaining)
        }, status=401)

async def api_auth_logout(request):
    resp = web.json_response({"success": True})
    resp.del_cookie("tapo_session")
    return resp

async def api_set_pin(request):
    if not is_authenticated(request):
        cfg = load_config()
        if cfg.get("security", {}).get("pin_set", False):
            return web.json_response({"error": "Unauthorized"}, status=401)

    try:
        data = await request.json()
        new_pin = str(data.get("pin", "")).strip()
        if len(new_pin) < 4:
            return web.json_response({"success": False, "error": "PIN must be at least 4 digits"}, status=400)
    except Exception:
        return web.json_response({"success": False, "error": "Invalid data"}, status=400)

    cfg = load_config()
    cfg.setdefault("security", {})["pin"] = new_pin
    cfg["security"]["pin_set"] = True
    save_config(cfg)

    now = time.time()
    expiry = now + (cfg["security"].get("session_timeout_minutes", 1440) * 60)
    token = make_session_token(expiry)

    resp = web.json_response({"success": True, "message": "PIN updated successfully"})
    resp.set_cookie("tapo_session", token, max_age=86400, httponly=True, samesite="Lax")
    return resp

async def api_get_config(request):
    if not is_authenticated(request):
        return web.json_response({"error": "Unauthorized"}, status=401)
    
    cfg = load_config()
    cam = cfg.get("camera", {})
    masked_cfg = {
        "ip": cam.get("ip", ""),
        "username": cam.get("username", ""),
        "has_password": bool(cam.get("password")),
        "rtsp_port": cam.get("rtsp_port", 554),
        "stream_hd": cam.get("stream_hd", "stream1"),
        "stream_sd": cam.get("stream_sd", "stream2")
    }
    return web.json_response(masked_cfg)

async def api_save_config(request):
    if not is_authenticated(request):
        cfg = load_config()
        if cfg.get("security", {}).get("pin_set", False):
            return web.json_response({"error": "Unauthorized"}, status=401)

    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)

    cfg = load_config()
    cam = cfg.setdefault("camera", {})
    
    if "ip" in data:
        cam["ip"] = str(data["ip"]).strip()
    if "username" in data:
        cam["username"] = str(data["username"]).strip()
    if "password" in data and str(data["password"]).strip():
        cam["password"] = str(data["password"]).strip()
    if "rtsp_port" in data:
        cam["rtsp_port"] = int(data.get("rtsp_port", 554))

    save_config(cfg)
    restart_go2rtc()

    return web.json_response({"success": True, "message": "Camera configuration updated and engine restarted!"})

async def api_test_camera(request):
    if not is_authenticated(request):
        return web.json_response({"error": "Unauthorized"}, status=401)
    
    cfg = load_config()
    ip = cfg.get("camera", {}).get("ip", "").strip()
    port = int(cfg.get("camera", {}).get("rtsp_port", 554))

    if not ip:
        return web.json_response({"reachable": False, "error": "Camera IP is not set"})

    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2.5)
        res = s.connect_ex((ip, port))
        s.close()
        if res == 0:
            return web.json_response({"reachable": True, "message": f"Successfully connected to {ip}:{port} (RTSP Open)"})
        else:
            return web.json_response({"reachable": False, "error": f"Camera IP {ip} is unreachable on port {port}. Check IP address and Wi-Fi."})
    except Exception as e:
        return web.json_response({"reachable": False, "error": str(e)})

async def api_stream_status(request):
    if not is_authenticated(request):
        return web.json_response({"error": "Unauthorized"}, status=401)

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("http://127.0.0.1:1984/api/streams", timeout=2) as r:
                if r.status == 200:
                    data = await r.json()
                    hd_online = "tapo_hd" in data and data["tapo_hd"] is not None
                    sd_online = "tapo_sd" in data and data["tapo_sd"] is not None
                    return web.json_response({
                        "engine_online": True,
                        "streams": data,
                        "hd_online": hd_online,
                        "sd_online": sd_online
                    })
    except Exception:
        pass
    
    return web.json_response({"engine_online": False, "hd_online": False, "sd_online": False})

async def api_snapshot(request):
    if not is_authenticated(request):
        return web.Response(status=401, text="Unauthorized")
    if privacy_mode_active:
        return web.Response(status=403, text="Confidential Mode is active - camera stream is off")
    
    src = request.query.get("src", "tapo_hd")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"http://127.0.0.1:1984/api/frame.jpeg?src={src}", timeout=5) as r:
                if r.status == 200:
                    img = await r.read()
                    filename = f"tapo_snapshot_{int(time.time())}.jpg"
                    return web.Response(
                        body=img,
                        content_type="image/jpeg",
                        headers={"Content-Disposition": f"attachment; filename={filename}"}
                    )
                else:
                    return web.Response(status=r.status, text="Snapshot not available. Make sure camera is online.")
    except Exception as e:
        return web.Response(status=500, text=f"Error capturing snapshot: {e}")

async def api_ptz_move(request):
    if not is_authenticated(request):
        return web.json_response({"error": "Unauthorized"}, status=401)
    if privacy_mode_active:
        return web.json_response({"success": False, "error": "Camera controls are locked while Confidential Mode is active"}, status=403)
    
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)
    
    direction = data.get("direction")
    step = data.get("step", 0.1)

    cfg = load_config()
    cam = cfg.get("camera", {})
    ip = cam.get("ip", "")
    user = cam.get("username", "")
    pwd = cam.get("password", "")

    if not ip or not user or not pwd:
        return web.json_response({"error": "Camera credentials not configured"}, status=400)

    loop = asyncio.get_running_loop()
    success, msg = await loop.run_in_executor(None, ptz.ptz_move, ip, user, pwd, direction, step)
    return web.json_response({"success": success, "message": msg})

async def api_privacy_status(request):
    if not is_authenticated(request):
        return web.json_response({"error": "Unauthorized"}, status=401)
    return web.json_response({"active": privacy_mode_active})

async def api_privacy_toggle(request):
    global privacy_mode_active
    if not is_authenticated(request):
        return web.json_response({"error": "Unauthorized"}, status=401)
    
    try:
        data = await request.json()
        enable = data.get("enable")
        if enable is None:
            enable = not privacy_mode_active
    except Exception:
        enable = not privacy_mode_active
    
    privacy_mode_active = bool(enable)
    
    # Close any currently connected client WebSockets so stream stops immediately
    if privacy_mode_active:
        for ws in list(active_ws_clients):
            try:
                asyncio.create_task(ws.close(code=1000, message=b"Privacy mode activated"))
            except Exception:
                pass
        active_ws_clients.clear()

    cfg = load_config()
    cam = cfg.get("camera", {})
    ip = cam.get("ip", "")
    user = cam.get("username", "")
    pwd = cam.get("password", "")

    msg = "Confidential mode activated" if privacy_mode_active else "Confidential mode deactivated"
    if ip and user and pwd:
        loop = asyncio.get_running_loop()
        if privacy_mode_active:
            # Physically tilt camera all the way down to base (like in Tapo app)
            await loop.run_in_executor(None, ptz.ptz_privacy_down, ip, user, pwd)
        else:
            # Bring camera back up to eye-level horizontal view
            await loop.run_in_executor(None, ptz.ptz_privacy_up, ip, user, pwd)

    return web.json_response({"success": True, "active": privacy_mode_active, "message": msg})

async def handle_webrtc_proxy(request):
    if not is_authenticated(request):
        return web.Response(status=401, text="Unauthorized")
    if privacy_mode_active:
        return web.Response(status=403, text="Confidential Mode is active")
    src = request.query.get("src", "tapo_hd")
    body = await request.read()
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(f"http://127.0.0.1:1984/api/webrtc?src={src}", data=body, headers={"Content-Type": request.content_type or "text/plain"}) as r:
                data = await r.read()
                return web.Response(body=data, status=r.status, content_type=r.content_type)
    except Exception as e:
        return web.Response(status=500, text=str(e))

active_ws_clients = set()

async def handle_ws_proxy(request):
    if not is_authenticated(request):
        return web.Response(status=401, text="Unauthorized")
    if privacy_mode_active:
        return web.Response(status=403, text="Confidential Mode is active")

    src = request.query.get("src", "tapo_hd")
    ws_client = web.WebSocketResponse(max_msg_size=16*1024*1024)
    await ws_client.prepare(request)

    active_ws_clients.add(ws_client)

    backend_url = f"http://127.0.0.1:1984/api/ws?src={src}"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(backend_url, max_msg_size=16*1024*1024) as ws_backend:
                async def client_to_backend():
                    try:
                        async for msg in ws_client:
                            if ws_backend.closed:
                                break
                            if msg.type == aiohttp.WSMsgType.TEXT:
                                await ws_backend.send_str(msg.data)
                            elif msg.type == aiohttp.WSMsgType.BINARY:
                                await ws_backend.send_bytes(msg.data)
                            elif msg.type in (aiohttp.WSMsgType.CLOSE, aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                                break
                    except Exception:
                        pass

                async def backend_to_client():
                    try:
                        async for msg in ws_backend:
                            if ws_client.closed:
                                break
                            if msg.type == aiohttp.WSMsgType.TEXT:
                                await ws_client.send_str(msg.data)
                            elif msg.type == aiohttp.WSMsgType.BINARY:
                                await ws_client.send_bytes(msg.data)
                            elif msg.type in (aiohttp.WSMsgType.CLOSE, aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                                break
                    except Exception:
                        pass

                t1 = asyncio.create_task(client_to_backend())
                t2 = asyncio.create_task(backend_to_client())
                done, pending = await asyncio.wait([t1, t2], return_when=asyncio.FIRST_COMPLETED)
                for task in pending:
                    task.cancel()
    except Exception:
        pass
    finally:
        active_ws_clients.discard(ws_client)

    return ws_client

def init_app():
    app = web.Application()
    
    app.router.add_get("/", handle_index)
    app.router.add_get("/api/auth/check", api_auth_check)
    app.router.add_post("/api/auth/login", api_auth_login)
    app.router.add_post("/api/auth/logout", api_auth_logout)
    app.router.add_post("/api/auth/set_pin", api_set_pin)
    
    app.router.add_get("/api/config", api_get_config)
    app.router.add_post("/api/config", api_save_config)
    app.router.add_get("/api/camera/test", api_test_camera)
    app.router.add_get("/api/stream/status", api_stream_status)
    app.router.add_get("/api/snapshot", api_snapshot)
    app.router.add_post("/api/ptz/move", api_ptz_move)
    app.router.add_get("/api/privacy/status", api_privacy_status)
    app.router.add_post("/api/privacy/toggle", api_privacy_toggle)
    
    app.router.add_get("/ws", handle_ws_proxy)
    app.router.add_get("/api/ws", handle_ws_proxy)
    app.router.add_post("/api/webrtc", handle_webrtc_proxy)
    
    STATIC_DIR.mkdir(exist_ok=True)
    app.router.add_static("/static/", path=str(STATIC_DIR), name="static")

    return app

if __name__ == "__main__":
    if sys.stdout.encoding.lower() != 'utf-8':
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass

    cfg = load_config()
    print("==================================================")
    print("[*] TAPO C510W SECURE PRIVATE VIEWER (LOCAL EDITION)")
    print("==================================================")
    
    restart_go2rtc()
    print("[+] go2rtc engine launched on 127.0.0.1:1984")
    
    host = cfg.get("server", {}).get("host", "0.0.0.0")
    port = cfg.get("server", {}).get("port", 5000)
    
    print(f"[+] Security Dashboard available at: http://localhost:{port}")
    print("==================================================")
    
    app = init_app()
    try:
        web.run_app(app, host=host, port=port)
    finally:
        if go2rtc_process:
            go2rtc_process.terminate()
