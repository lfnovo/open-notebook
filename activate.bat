@echo off
echo Starting all dev services...

REM ── Backend (conda env activate karva sathe) ──────────────────
start "Backend" cmd /k "call conda activate C:\Bhavesh\env && uv run uvicorn api.main:app --host 127.0.0.1 --port 5055"

REM ── SurrealDB ─────────────────────────────────────────────────
start "SurrealDB" cmd /k "C:\surrealdb\surreal.exe start --log info --user root --pass root rocksdb://./surreal_data"

REM ── Frontend ──────────────────────────────────────────────────
start "Frontend" cmd /k "npm run dev"

REM ── Zookeeper ─────────────────────────────────────────────────
start "Zookeeper" cmd /k "cd /d C:\kafka\kafka && .\bin\windows\zookeeper-server-start.bat .\config\zookeeper.properties"

REM ── Kafka Server ──────────────────────────────────────────────
start "Kafka" cmd /k "cd /d C:\kafka\kafka && .\bin\windows\kafka-server-start.bat .\config\server.properties"

REM ── Surreal Commands Worker (conda env activate karva sathe) ──
start "Surreal Worker" cmd /k "call conda activate C:\Bhavesh\env && uv run --env-file .env surreal-commands-worker --import-modules commands"

echo.
echo All 6 services started!
pause