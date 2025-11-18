# Open Notebook Development Script for Windows PowerShell
# This script provides Windows equivalents for Makefile commands

param(
    [Parameter(Position=0)]
    [string]$Command = "help"
)

# Color output functions
function Write-Info {
    param([string]$Message)
    Write-Host $Message -ForegroundColor Cyan
}

function Write-Success {
    param([string]$Message)
    Write-Host $Message -ForegroundColor Green
}

function Write-Error-Message {
    param([string]$Message)
    Write-Host $Message -ForegroundColor Red
}

# Get version from pyproject.toml
function Get-Version {
    $content = Get-Content -Path "pyproject.toml" -Raw
    if ($content -match 'version\s*=\s*"([^"]+)"') {
        return $Matches[1]
    }
    return "unknown"
}

# Command implementations
function Start-Database {
    Write-Info "📊 Starting SurrealDB with Docker Compose..."
    docker compose up -d surrealdb
}

function Start-Frontend {
    Write-Info "🌐 Starting Next.js frontend..."
    Write-Info "⚠️  Warning: Starting frontend only. For full functionality, use 'start-all'"
    Set-Location frontend
    npm run dev
    Set-Location ..
}

function Start-API {
    Write-Info "🔧 Starting FastAPI backend..."
    uv run run_api.py
}

function Start-Worker {
    Write-Info "⚙️ Starting background worker..."
    uv run --env-file .env surreal-commands-worker --import-modules commands
}

function Stop-Worker {
    Write-Info "🛑 Stopping background worker..."
    Get-Process | Where-Object {$_.CommandLine -like "*surreal-commands-worker*"} | Stop-Process -Force
}

function Restart-Worker {
    Stop-Worker
    Start-Sleep -Seconds 2
    Start-Worker
}

function Start-All {
    Write-Info "🚀 Starting Open Notebook (Database + API + Worker + Frontend)..."

    Write-Info "📊 Starting SurrealDB..."
    docker compose up -d surrealdb
    Start-Sleep -Seconds 3

    Write-Info "🔧 Starting API backend in background..."
    Start-Job -ScriptBlock {
        Set-Location $using:PWD
        uv run run_api.py
    } -Name "OpenNotebook-API"
    Start-Sleep -Seconds 3

    Write-Info "⚙️ Starting background worker..."
    Start-Job -ScriptBlock {
        Set-Location $using:PWD
        uv run --env-file .env surreal-commands-worker --import-modules commands
    } -Name "OpenNotebook-Worker"
    Start-Sleep -Seconds 2

    Write-Info "🌐 Starting Next.js frontend..."
    Write-Success "✅ All services started!"
    Write-Info "📱 Frontend: http://localhost:3000"
    Write-Info "🔗 API: http://localhost:5055"
    Write-Info "📚 API Docs: http://localhost:5055/docs"
    Write-Info ""
    Write-Info "To view background job logs:"
    Write-Info "  Get-Job | Receive-Job -Keep"
    Write-Info ""
    Write-Info "To stop background jobs:"
    Write-Info "  .\scripts\dev.ps1 stop-all"
    Write-Info ""

    Set-Location frontend
    npm run dev
    Set-Location ..
}

function Stop-All {
    Write-Info "🛑 Stopping all Open Notebook services..."

    # Stop PowerShell jobs
    Get-Job -Name "OpenNotebook-*" -ErrorAction SilentlyContinue | Stop-Job
    Get-Job -Name "OpenNotebook-*" -ErrorAction SilentlyContinue | Remove-Job

    # Stop processes by name/pattern
    Get-Process | Where-Object {$_.ProcessName -like "*node*" -and $_.CommandLine -like "*next dev*"} -ErrorAction SilentlyContinue | Stop-Process -Force
    Get-Process | Where-Object {$_.CommandLine -like "*surreal-commands-worker*"} -ErrorAction SilentlyContinue | Stop-Process -Force
    Get-Process | Where-Object {$_.CommandLine -like "*run_api.py*"} -ErrorAction SilentlyContinue | Stop-Process -Force
    Get-Process | Where-Object {$_.CommandLine -like "*uvicorn*"} -ErrorAction SilentlyContinue | Stop-Process -Force

    # Stop Docker services
    docker compose down

    Write-Success "✅ All services stopped!"
}

function Show-Status {
    Write-Info "📊 Open Notebook Service Status:"

    Write-Host "`nDatabase (SurrealDB):"
    $dbStatus = docker compose ps surrealdb 2>$null
    if ($LASTEXITCODE -eq 0 -and $dbStatus) {
        Write-Success "  ✅ Running"
    } else {
        Write-Error-Message "  ❌ Not running"
    }

    Write-Host "`nAPI Backend:"
    $apiProcess = Get-Process | Where-Object {$_.CommandLine -like "*run_api.py*" -or $_.CommandLine -like "*uvicorn api.main:app*"} -ErrorAction SilentlyContinue
    if ($apiProcess) {
        Write-Success "  ✅ Running"
    } else {
        Write-Error-Message "  ❌ Not running"
    }

    Write-Host "`nBackground Worker:"
    $workerProcess = Get-Process | Where-Object {$_.CommandLine -like "*surreal-commands-worker*"} -ErrorAction SilentlyContinue
    if ($workerProcess) {
        Write-Success "  ✅ Running"
    } else {
        Write-Error-Message "  ❌ Not running"
    }

    Write-Host "`nNext.js Frontend:"
    $frontendProcess = Get-Process | Where-Object {$_.ProcessName -like "*node*" -and $_.CommandLine -like "*next dev*"} -ErrorAction SilentlyContinue
    if ($frontendProcess) {
        Write-Success "  ✅ Running"
    } else {
        Write-Error-Message "  ❌ Not running"
    }

    Write-Host "`nPowerShell Background Jobs:"
    $jobs = Get-Job -Name "OpenNotebook-*" -ErrorAction SilentlyContinue
    if ($jobs) {
        $jobs | Format-Table -Property Name, State, HasMoreData
    } else {
        Write-Info "  No background jobs running"
    }
}

function Invoke-Lint {
    Write-Info "🔍 Running type checking with mypy..."
    uv run python -m mypy .
}

function Invoke-Ruff {
    Write-Info "🔍 Running ruff linting..."
    ruff check . --fix
}

function Clear-Cache {
    Write-Info "🧹 Cleaning cache directories..."
    Get-ChildItem -Path . -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force
    Get-ChildItem -Path . -Recurse -Directory -Filter ".mypy_cache" | Remove-Item -Recurse -Force
    Get-ChildItem -Path . -Recurse -Directory -Filter ".ruff_cache" | Remove-Item -Recurse -Force
    Get-ChildItem -Path . -Recurse -Directory -Filter ".pytest_cache" | Remove-Item -Recurse -Force
    Get-ChildItem -Path . -Recurse -File -Filter "*.pyc" | Remove-Item -Force
    Get-ChildItem -Path . -Recurse -File -Filter "*.pyo" | Remove-Item -Force
    Get-ChildItem -Path . -Recurse -File -Filter "*.pyd" | Remove-Item -Force
    Write-Success "✅ Cache directories cleaned!"
}

function Export-Documentation {
    Write-Info "📚 Exporting documentation..."
    uv run python scripts/export_docs.py
    Write-Success "✅ Documentation export complete!"
}

function Show-Help {
    $version = Get-Version
    Write-Host ""
    Write-Info "Open Notebook Development Script (v$version)"
    Write-Host ""
    Write-Host "Usage: .\scripts\dev.ps1 <command>"
    Write-Host ""
    Write-Host "Available commands:"
    Write-Host ""
    Write-Host "  Service Management:"
    Write-Host "    start-all          Start all services (Database, API, Worker, Frontend)"
    Write-Host "    stop-all           Stop all running services"
    Write-Host "    status             Show status of all services"
    Write-Host ""
    Write-Host "  Individual Services:"
    Write-Host "    database           Start SurrealDB database only"
    Write-Host "    api                Start FastAPI backend only"
    Write-Host "    frontend           Start Next.js frontend only"
    Write-Host "    worker             Start background worker"
    Write-Host "    worker-stop        Stop background worker"
    Write-Host "    worker-restart     Restart background worker"
    Write-Host ""
    Write-Host "  Development Tools:"
    Write-Host "    lint               Run mypy type checking"
    Write-Host "    ruff               Run ruff linting and fixes"
    Write-Host "    clean-cache        Remove all Python cache directories"
    Write-Host "    export-docs        Export documentation"
    Write-Host ""
    Write-Host "  Information:"
    Write-Host "    help               Show this help message"
    Write-Host ""
    Write-Host "Examples:"
    Write-Host "  .\scripts\dev.ps1 start-all      # Start all services"
    Write-Host "  .\scripts\dev.ps1 status         # Check service status"
    Write-Host "  .\scripts\dev.ps1 stop-all       # Stop everything"
    Write-Host ""
}

# Main command router
switch ($Command.ToLower()) {
    "database" { Start-Database }
    "frontend" { Start-Frontend }
    "run" { Start-Frontend }
    "api" { Start-API }
    "worker" { Start-Worker }
    "worker-start" { Start-Worker }
    "worker-stop" { Stop-Worker }
    "worker-restart" { Restart-Worker }
    "start-all" { Start-All }
    "stop-all" { Stop-All }
    "status" { Show-Status }
    "lint" { Invoke-Lint }
    "ruff" { Invoke-Ruff }
    "clean-cache" { Clear-Cache }
    "export-docs" { Export-Documentation }
    "help" { Show-Help }
    default {
        Write-Error-Message "Unknown command: $Command"
        Write-Host ""
        Show-Help
    }
}
