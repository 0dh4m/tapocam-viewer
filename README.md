# 📹 Tapo C510W Private Security Viewer

<div align="center">

[![Author](https://img.shields.io/badge/Author-0dh4m-00E5FF?style=for-the-badge&logo=github&logoColor=white)](https://github.com/0dh4m)
[![Camera](https://img.shields.io/badge/Camera-TP--Link%20Tapo%20C510W-7928CA?style=for-the-badge)](https://github.com/0dh4m/tapocam-viewer)
[![Streaming](https://img.shields.io/badge/Stream-WebRTC%20%7C%20RTSP%20%7C%20go2rtc-FF0080?style=for-the-badge)](https://github.com/0dh4m/tapocam-viewer)
[![Protocol](https://img.shields.io/badge/Protocol-ONVIF%20WSSE%20PTZ-success?style=for-the-badge)](https://github.com/0dh4m/tapocam-viewer)
[![License](https://img.shields.io/badge/License-Proprietary-red?style=for-the-badge)](LICENSE)

**A local web dashboard for the TP-Link Tapo C510W outdoor pan/tilt camera.**
Low-latency WebRTC video through `go2rtc`, ONVIF WSSE PTZ control, snapshots, audio, a PIN lock and a privacy shutter.

[Features](#-features) • [Architecture](#-architecture) • [Setup](#-setup) • [Controls](#-controls) • [Security](#-security-notes)

</div>

> **Disclaimer:** this is an independent project, not affiliated with or endorsed by TP-Link. Tested with the Tapo C510W; other ONVIF Profile S cameras may work but are not guaranteed.

---

## ✨ Features

- 🎥 **Two live streams** — `stream1` (2K HD) and `stream2` (SD), served as WebRTC through `go2rtc`.
- 🕹️ **ONVIF PTZ D-pad** — pan and tilt with adjustable step size (Fine / Normal / Fast).
- 🔐 **PIN lock** — 4+ digit PIN, configurable failed-attempt limit and lockout window.
- 🛡️ **Privacy mode** — sends the ONVIF privacy command to shutter the camera, with a full-screen overlay (`C` key).
- 📸 **Instant snapshot** — downloads a JPEG frame from the live stream.
- 🔊 **Camera audio toggle**, fullscreen mode and a live connection/status panel.
- ⚙️ **In-browser setup** — camera IP, credentials, RTSP ports and stream names can be saved from the settings panel.
- 🧪 **Camera connectivity test** before saving.
- 🏠 **LAN-first** — runs on your machine and is intended for local/VPN access.

> **Not implemented:** optical/digital zoom, preset positions, patrol routes, motion tracking or cloud recording. The C510W has no optical zoom, and this project does not add one.

---

## 🏗️ Architecture

```text
┌─────────────────────────────────┐
│     TP-Link Tapo C510W camera   │
└────────────────┬────────────────┘
                 │
       ┌─────────┴─────────┐
       ▼                   ▼
┌──────────────┐    ┌──────────────┐
│  RTSP feed   │    │  ONVIF SOAP  │
│  port 554    │    │  port 2020   │
└──────┬───────┘    └──────┬───────┘
       │                   │
       ▼                   ▼
┌──────────────┐    ┌──────────────┐
│ go2rtc       │    │ aiohttp PTZ  │
│ WebRTC proxy │    │ WSSE service │
└──────┬───────┘    └──────┬───────┘
       │                   │
       └─────────┬─────────┘
                 ▼
┌─────────────────────────────────┐
│  Browser dashboard (static/)    │
│  • WebRTC player                │
│  • PTZ D-pad + keyboard arrows  │
│  • PIN lock / privacy mode      │
│  • Snapshot + audio + fullscreen│
└─────────────────────────────────┘
```

- **Backend:** Python 3 + `aiohttp` (`server.py`), ONVIF SOAP client (`ptz.py`).
- **Media:** [`go2rtc`](https://github.com/AlexxIT/go2rtc) converts RTSP to WebRTC and serves the player.
- **Frontend:** vanilla HTML/CSS/JS in `static/`.

---

## 🚀 Setup

### 1. Requirements

- Windows 10/11 (the launcher and `go2rtc.exe` path are Windows-oriented).
- Python **3.10+**.
- A Tapo C510W (or compatible ONVIF camera) on the same network.
- A **Camera Account** created in the Tapo app: *Settings → Advanced Settings → Camera Account*.

### 2. Install Python dependencies

```bash
git clone https://github.com/0dh4m/tapocam-viewer.git
cd tapocam-viewer
python -m pip install -r requirements.txt
```

### 3. Add `go2rtc`

Download the Windows binary from the [go2rtc releases page](https://github.com/AlexxIT/go2rtc/releases) and place it in the repository root as:

```text
tapocam-viewer/
└── go2rtc.exe
```

The server generates `go2rtc.yaml` at startup from your camera settings. If `go2rtc.exe` is missing, the dashboard still starts but the video stream will not.

### 4. Configure the camera

Copy the example and edit it:

```bash
copy config.json.example config.json
```

```json
{
  "camera": {
    "ip": "192.168.1.100",
    "username": "your_tapo_username",
    "password": "YOUR_TAPO_PASSWORD",
    "rtsp_port": 554,
    "stream_hd": "stream1",
    "stream_sd": "stream2"
  },
  "security": {
    "pin": "0000",
    "pin_set": false,
    "session_timeout_minutes": 1440,
    "max_failed_attempts": 5,
    "lockout_minutes": 5
  },
  "server": {
    "host": "0.0.0.0",
    "port": 5000
  }
}
```

You can also change the camera settings from the dashboard after the first launch.

### 5. Start the server

```cmd
scripts\start.bat
```

Or manually:

```bash
python server.py
```

Open **http://localhost:5000**. On first launch, set your own PIN in the dashboard.

---

## 🕹️ Controls

| Action | Control |
| :--- | :--- |
| Pan / tilt | On-screen D-pad or **arrow keys** |
| PTZ step size | Fine / Normal / Fast buttons in the PTZ panel |
| Privacy shutter | `C` key or the **Privacy** button |
| Snapshot | Camera button in the video toolbar |
| Audio on/off | Speaker button |
| Fullscreen | Fullscreen button |
| Lock dashboard | **Lock** button |

---

## 📂 Project Structure

```text
tapocam-viewer/
├── server.py              # aiohttp app, auth, config, go2rtc and WebRTC proxy
├── ptz.py                 # ONVIF WSSE SOAP client (pan/tilt, privacy, status)
├── config.json.example    # camera, security and server settings
├── requirements.txt
├── go2rtc.yaml            # generated at runtime (not committed)
├── scripts/start.bat      # Windows launcher
└── static/
    ├── index.html         # dashboard
    ├── app.js             # UI, PTZ, PIN lock, privacy, snapshots
    ├── style.css
    ├── video-rtc.js
    └── video-stream.js
```

---

## 🔐 Security Notes

- `config.json` contains the camera password. It is **git-ignored** — never commit it.
- `go2rtc.yaml` is generated from `config.json` and is also **git-ignored**.
- Change the default PIN on first launch. The PIN protects the dashboard, not the camera stream itself.
- The server binds to `0.0.0.0` so other devices on your LAN can use it. Do **not** expose port `5000` directly to the internet; use a VPN (WireGuard/Tailscale) or an authenticated reverse proxy.
- Privacy mode depends on the camera accepting the ONVIF privacy command.
- Rotate the camera password if a config file was ever committed or shared.

---

## ⚠️ Known Limitations

- The Tapo C510W has **no optical zoom**; the dashboard intentionally exposes pan/tilt only.
- Presets, patrol routes and motion tracking are not implemented.
- WebRTC may need UDP ports open on the local network; `go2rtc` handles negotiation.
- Only tested on Windows with the C510W. ONVIF implementations vary by firmware.

---

## 👤 Author

**Adham Cherkaoui Eddeqaqi (0dh4m)**
- 🌐 Portfolio: [0dh4m.github.io](https://0dh4m.github.io/)
- 🐙 GitHub: [@0dh4m](https://github.com/0dh4m)
- ✉️ Email: 0dh4mm@gmail.com

---

## 📄 License

Proprietary and confidential — see [LICENSE](LICENSE). Unauthorized copying or distribution is prohibited.

*Copyright © 2026 Adham Cherkaoui Eddeqaqi (0dh4m). All rights reserved.*
