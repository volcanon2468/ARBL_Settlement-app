@echo off
setlocal

:: Check if the frontend is already running on port 3000
netstat -ano | findstr "LISTENING" | findstr ":3000" >nul
if %errorlevel% equ 0 (
    echo The application is already running!
    start http://localhost:3000/login
    exit /b 0
)

echo ===================================================
echo   Starting Settlement App (Backend ^& Frontend)
echo ===================================================

:: Start Backend in a new window
echo Starting FastAPI Backend on port 8000...
cd /d "%~dp0backend"
start "Settlement Backend Server" cmd /k ".\venv\Scripts\activate && uvicorn app.main:app --host 127.0.0.1 --port 8000"

:: Start Frontend in a new window
echo Starting Next.js Frontend on port 3000...
cd /d "%~dp0frontend"
start "Settlement Frontend Server" cmd /k "npm run dev"

:: Wait for port 3000 to become active before opening browser
echo Waiting for servers to initialize (this may take a few seconds)...
:waitForPort
ping 127.0.0.1 -n 3 >nul
netstat -ano | findstr "LISTENING" | findstr ":3000" >nul
if %errorlevel% neq 0 goto waitForPort

:: Open the browser
echo Servers are running! Opening browser...
start http://localhost:3000/login

exit /b 0
