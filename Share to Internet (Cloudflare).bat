@echo off
title Visual Bulk Certificate Generator - Internet Tunnel
cd /d "%~dp0"

echo ========================================================
echo  SHARING VISUAL BULK CERTIFICATE GENERATOR TO INTERNET
echo ========================================================
echo.

:: 1. Start Web Server in background if not already running
echo [1/2] Starting local web server on port 8000...
start /b python server.py > server.log 2>&1
timeout /t 3 >nul

:: 2. Check for cloudflared
if not exist "cloudflared.exe" (
    echo [2/2] Downloading free Cloudflare tunnel utility (one-time setup)...
    powershell -Command "Invoke-WebRequest -Uri 'https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe' -OutFile 'cloudflared.exe'"
)

echo.
echo ========================================================
echo  STARTING PUBLIC HTTPS INTERNET TUNNEL (100%% FREE)
echo ========================================================
echo Your public HTTPS link will appear below:
echo (Share this link with anyone on the internet to use the app)
echo ========================================================
echo.

cloudflared.exe tunnel --url http://127.0.0.1:8000
pause
