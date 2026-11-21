# 📹 TapoCam PTZ Viewer & Real-Time WebRTC Security Deck

<div align="center">

[![Author](https://img.shields.io/badge/Author-0dh4m-00E5FF?style=for-the-badge&logo=github&logoColor=white)](https://github.com/0dh4m)
[![Camera](https://img.shields.io/badge/Camera-TP--Link%20Tapo%20C510W-7928CA?style=for-the-badge)](https://github.com/0dh4m/tapocam-viewer)
[![Streaming](https://img.shields.io/badge/Stream-WebRTC%20%7C%20RTSP%20%7C%20go2rtc-FF0080?style=for-the-badge)](https://github.com/0dh4m/tapocam-viewer)
[![Protocol](https://img.shields.io/badge/Protocol-ONVIF%20WSSE%20PTZ-success?style=for-the-badge)](https://github.com/0dh4m/tapocam-viewer)

**A high-performance surveillance and camera control station engineered for the TP-Link Tapo C510W Outdoor Pan/Tilt Security Camera.**  
Combines sub-second WebRTC video streaming with native ONVIF WSSE hardware PTZ control, virtual joystick, snapshot capture, and patrol presets.

[Key Features](#-key-features) • [Architecture](#-architecture) • [Controls](#-controls--shortcuts) • [Quickstart](#-quickstart-guide)

</div>

---

## 🌟 Key Features

- ⚡ **Sub-Second Low-Latency WebRTC Stream**: Powered by an embedded `go2rtc` media pipeline, reducing RTSP video stream lag from several seconds down to under **150ms**.
- 🕹️ **Interactive Hardware PTZ Joystick**: Responsive 360-degree virtual joystick supporting fluid continuous Pan, Tilt, and Zoom navigation.
- 🔐 **ONVIF WSSE Secure Authentication**: Custom SOAP XML command dispatcher with UsernameToken, PasswordDigest, Nonce, and Created timestamps.
- 🎯 **Presets & Fast Patrol**: Store and instantly recall target camera coordinates (Front Gate, Driveway, Backyard, Entrance).
- 📸 **Live High-Res Snapshots**: Capture timestamped Full-HD frames directly from the live feed and save to disk with one click.
- ⌨️ **Keyboard Navigation**: Steer the camera effortlessly using `WASD` or Arrow keys with dynamic velocity scaling.

---

## 🏗️ Architecture

```text
┌─────────────────────────────────┐
│     TP-Link Tapo C510W Cam      │
└────────────────┬────────────────┘
                 │
       ┌─────────┴─────────┐
       ▼                   ▼
┌──────────────┐    ┌──────────────┐
│  RTSP Feed   │    │  ONVIF SOAP  │
│  (Port 554)  │    │ (Port 2020)  │
└──────┬───────┘    └──────┬───────┘
       │                   │
       ▼                   ▼
┌──────────────┐    ┌──────────────┐
│ go2rtc Core  │    │ Flask PTZ Svc│
│ WebRTC Proxy │    │ ONVIF WSSE   │
└──────┬───────┘    └──────┬───────┘
       │                   │
       └─────────┬─────────┘
                 ▼
┌─────────────────────────────────┐
│     Modern Glassmorphic UI      │
│   • Sub-150ms WebRTC Video Feed │
│   • Responsive Virtual Joystick │
│   • Keyboard Hotkeys (WASD)     │
└─────────────────────────────────┘
```

---

## 🕹️ Controls & Shortcuts

| Action | Control / Key | Description |
| :--- | :--- | :--- |
| **Pan Left / Right** | `A` / `D` or `←` / `→` | Rotates the camera horizontally |
| **Tilt Up / Down** | `W` / `S` or `↑` / `↓` | Adjusts camera vertical elevation |
| **Zoom In / Out** | `+` / `-` | Hardware optical / digital zoom steps |
| **Snapshot** | `Space` or Click `📷` | Saves high-resolution JPEG capture |
| **Home Position** | `H` | Resets camera to primary patrol coordinate |

---

## 🚀 Quickstart Guide

### 1. Requirements
- Python 3.10+
- TP-Link Tapo C510W (or any ONVIF Profile S compatible camera) connected to your local network.
- Camera Account created in the Tapo App (*Settings -> Advanced Settings -> Camera Account*).

### 2. Configuration
Copy `config.json.example` to `config.json` and enter your camera credentials:
```json
{
  "camera_ip": "192.168.1.100",
  "camera_port": 2020,
  "rtsp_port": 554,
  "username": "your_tapo_username",
  "password": "your_tapo_password"
}
```

### 3. Launch the Station
Run the automated launcher:
```cmd
scripts/start.bat
```
Or start manually:
```bash
python server.py
```
Open `http://localhost:8080` in your web browser.

---

## 👤 Author & Copyright

**Adham Cherkaoui Eddeqaqi (0dh4m)**  
- 🌐 Portfolio: [0dh4m.github.io/portfolio](https://0dh4m.github.io/portfolio)
- 🐙 GitHub: [@0dh4m](https://github.com/0dh4m)
- 📧 Email: 0dh4mm@gmail.com

*Copyright © 2026 Adham Cherkaoui Eddeqaqi (0dh4m). All rights reserved.*
