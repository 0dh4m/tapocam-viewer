@echo off
title Tapo C510W Secure Viewer
color 0b
echo ========================================================
echo   TAPO C510W PRIVATE SECURITY VIEWER (LOCAL EDITION)
echo ========================================================
echo.
cd /d "%~dp0"

echo [*] Starting Server and Streaming Engine...
start "" http://localhost:5000
python server.py

pause
