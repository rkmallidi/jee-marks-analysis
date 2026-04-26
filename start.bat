rks ate is allowed only @echo off
title JEE Analytics Platform

echo Starting JEE Analytics Platform...
echo.

:: Backend
start "Backend - FastAPI" cmd /k "cd /d "%~dp0backend" && "%~dp0.venv\Scripts\uvicorn.exe" app.main:app --reload --host 0.0.0.0 --port 8000"

:: Small delay so backend window opens first
timeout /t 2 /nobreak >nul

:: Frontend
start "Frontend - Vite" cmd /k "cd /d "%~dp0frontend" && npm run dev"

echo.
echo  Backend  : http://localhost:8000
echo  Frontend : http://localhost:5173
echo  API Docs : http://localhost:8000/docs
echo.
echo Both servers are starting in separate windows.
echo Close those windows (or press Ctrl+C in each) to stop.
echo.
pause
