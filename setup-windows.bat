@echo off
REM Open Notebook - Windows Quick Setup Script
REM This script helps set up Open Notebook on Windows systems

setlocal enabledelayedexpansion

echo.
echo ================================
echo Open Notebook - Windows Setup
echo ================================
echo.

REM Check if Docker is installed
where docker >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Docker is not installed or not in PATH
    echo Please install Docker Desktop from: https://www.docker.com/products/docker-desktop/
    echo.
    pause
    exit /b 1
)

echo [OK] Docker is installed
echo.

REM Check if Docker is running
docker info >nul 2>nul
if %errorlevel% neq 0 (
    echo [WARNING] Docker is not running
    echo Please start Docker Desktop and run this script again
    echo.
    pause
    exit /b 1
)

echo [OK] Docker is running
echo.

REM Create project directory structure
echo Creating project directories...
if not exist "notebook_data" mkdir notebook_data
if not exist "surreal_data" mkdir surreal_data

echo [OK] Directories created
echo.

REM Check if .env file exists
if not exist ".env" (
    if exist ".env.example" (
        echo Creating .env file from template...
        copy .env.example .env >nul
        echo [OK] .env file created from .env.example
        echo.
        echo IMPORTANT: Please edit .env file and add your API keys
        echo You need at least one AI provider API key (e.g., OPENAI_API_KEY)
        echo.
        echo Would you like to edit the .env file now? (Y/N)
        set /p EDIT_ENV=
        if /i "!EDIT_ENV!"=="Y" (
            if exist "C:\Windows\System32\notepad.exe" (
                notepad .env
            ) else (
                start .env
            )
        )
    ) else (
        echo [WARNING] .env.example not found
        echo Please create a .env file with your configuration
    )
) else (
    echo [OK] .env file already exists
)

echo.
echo Setup complete! You can now start Open Notebook using one of these methods:
echo.
echo Method 1: Docker Compose (Recommended)
echo   docker compose up -d
echo.
echo Method 2: Using PowerShell script (for development)
echo   PowerShell -ExecutionPolicy Bypass -File .\scripts\dev.ps1 start-all
echo.
echo After starting, access Open Notebook at: http://localhost:8502
echo API documentation will be available at: http://localhost:5055/docs
echo.
pause
