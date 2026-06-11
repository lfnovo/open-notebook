@echo off
REM Cross-platform dev launcher (Windows). Delegates to dev.py.
REM   dev.bat            bring everything up (combined logs, Ctrl+C stops all)
REM   dev.bat --skip-sync
REM   dev.bat stop       force-stop anything left running
cd /d "%~dp0"
uv run python dev.py %*
