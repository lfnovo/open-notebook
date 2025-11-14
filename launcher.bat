@echo off
REM Open Notebook Launcher Script for Windows
REM This script launches all required services for Open Notebook

setlocal enabledelayedexpansion

echo.
echo  ___                   _   _       _       _                 _
echo / _ \ _ __   ___ _ __ ^| \ ^| ^| ___ ^| ^|_ ___^| ^|__   ___   ___ ^| ^| __
echo ^| ^| ^| ^| '_ \ / _ \ '_ \^|  \^| ^|/ _ \^| __/ _ \ '_ \ / _ \ / _ \^| ^|/ /
echo ^| ^|_^| ^| ^|_) ^|  __/ ^| ^| ^| ^|\  ^| (_) ^| ^|^|  __/ ^|_) ^| (_) ^| (_) ^|   ^<
echo \___^| .__/ \___^|_^| ^|_^|_^| \_^|\___/ \__\___^|_.__/ \___/ \___/^|_^|\_\
echo      ^|_^|
echo.
echo Open Notebook Launcher
echo ======================
echo.

REM Check if we're in the right directory
if not exist "pyproject.toml" (
    echo [ERROR] Please run this script from the Open Notebook root directory
    exit /b 1
)

REM Check for required tools
echo [INFO] Checking for required tools...

REM Check for uv
where uv >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] uv is not installed.
    echo Please install uv from: https://astral.sh/uv
    echo.
    echo For Windows, run in PowerShell:
    echo powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    exit /b 1
)
echo [OK] uv found

REM Check for Node.js
where node >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Node.js is not installed.
    echo Please install Node.js 18+ from: https://nodejs.org/
    exit /b 1
)
for /f "tokens=*" %%i in ('node --version') do set NODE_VERSION=%%i
echo [OK] Node.js found (%NODE_VERSION%)

REM Check for npm
where npm >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] npm is not installed.
    echo Please install Node.js which includes npm.
    exit /b 1
)
for /f "tokens=*" %%i in ('npm --version') do set NPM_VERSION=%%i
echo [OK] npm found (%NPM_VERSION%)

REM Check for SurrealDB
where surreal >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [WARNING] SurrealDB is not installed.
    echo Please install SurrealDB from: https://surrealdb.com/install
    echo.
    echo For Windows, run in PowerShell:
    echo iwr https://windows.surrealdb.com -useb ^| iex
    exit /b 1
)
echo [OK] SurrealDB found

REM Check for .env file
if not exist ".env" (
    echo [WARNING] .env file not found.
    if exist ".env.example" (
        echo Creating .env from .env.example...
        copy .env.example .env >nul
        echo [OK] .env file created
        echo [WARNING] Please edit .env and add your API keys before continuing
        pause
    ) else (
        echo [ERROR] .env.example not found
        exit /b 1
    )
) else (
    echo [OK] .env file found
)

REM Install frontend dependencies if needed
if not exist "frontend\node_modules" (
    echo [INFO] Installing frontend dependencies...
    cd frontend
    call npm install
    cd ..
    echo [OK] Frontend dependencies installed
) else (
    echo [OK] Frontend dependencies already installed
)

REM Create data directories if they don't exist
if not exist "notebook_data" mkdir notebook_data
if not exist "surreal_data" mkdir surreal_data

echo.
echo [INFO] Starting Open Notebook services...
echo.

REM Start SurrealDB
echo [INFO] Starting SurrealDB...
start "SurrealDB" /MIN cmd /c "surreal start --log info --user root --pass root memory > surreal.log 2>&1"
timeout /t 2 /nobreak >nul
echo [OK] SurrealDB started (Port: 8000)

REM Start API
echo [INFO] Starting API backend...
start "Open Notebook API" /MIN cmd /c "uv run run_api.py > api.log 2>&1"
timeout /t 5 /nobreak >nul
echo [OK] API backend started (Port: 5055)

REM Start background worker
echo [INFO] Starting background worker...
start "Open Notebook Worker" /MIN cmd /c "uv run --env-file .env surreal-commands-worker --import-modules commands > worker.log 2>&1"
timeout /t 2 /nobreak >nul
echo [OK] Background worker started

REM Start frontend
echo [INFO] Starting Next.js frontend...
cd frontend
start "Open Notebook Frontend" /MIN cmd /c "npm run dev > ..\frontend.log 2>&1"
cd ..
timeout /t 5 /nobreak >nul
echo [OK] Next.js frontend started

REM Display success message
echo.
echo ========================================
echo   Open Notebook is now running!
echo ========================================
echo.
echo Access the application at:
echo   Frontend:  http://localhost:3000
echo   API:       http://localhost:5055
echo   API Docs:  http://localhost:5055/docs
echo.
echo Services are running in separate windows.
echo.
echo Log files:
echo   - surreal.log
echo   - api.log
echo   - worker.log
echo   - frontend.log
echo.
echo To stop all services:
echo   1. Close all Open Notebook command windows
echo   2. Or run: taskkill /F /FI "WINDOWTITLE eq Open Notebook*"
echo.
echo [INFO] Opening browser...
timeout /t 3 /nobreak >nul
start http://localhost:3000

echo.
echo Press any key to view the frontend log...
pause >nul
type frontend.log
