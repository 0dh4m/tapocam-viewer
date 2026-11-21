@echo off
title TapoCam Viewer & PTZ Gateway
cd /d "%~dp0\.."

echo ========================================================
echo        TapoCam Viewer - WebRTC & ONVIF PTZ Server
echo ========================================================
echo.

python --version >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH.
    pause
    exit /b 1
)

echo [INFO] Starting TapoCam Server...
python server.py

pause
