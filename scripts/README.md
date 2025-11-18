# Development Scripts

This directory contains helper scripts for developing Open Notebook.

---

## PowerShell Script (Windows)

### `dev.ps1` - Windows Development Helper

PowerShell script providing Windows equivalents of Makefile commands for Open Notebook development.

#### Requirements

- Windows 10 (version 2004+) or Windows 11
- PowerShell 5.1 or higher
- Docker Desktop
- Python 3.11+ (for development)
- Node.js 18+ (for frontend development)
- uv package manager

#### Installation

No installation required. The script is ready to use from the repository root.

#### Usage

```powershell
# From the repository root
.\scripts\dev.ps1 <command>
```

#### Available Commands

**Service Management:**
- `start-all` - Start all services (Database, API, Worker, Frontend)
- `stop-all` - Stop all running services
- `status` - Show status of all services

**Individual Services:**
- `database` - Start SurrealDB database only
- `api` - Start FastAPI backend only
- `frontend` or `run` - Start Next.js frontend only
- `worker` - Start background worker
- `worker-stop` - Stop background worker
- `worker-restart` - Restart background worker

**Development Tools:**
- `lint` - Run mypy type checking
- `ruff` - Run ruff linting and fixes
- `clean-cache` - Remove all Python cache directories
- `export-docs` - Export documentation

**Information:**
- `help` - Show help message with all commands

#### Examples

```powershell
# Start all services for development
.\scripts\dev.ps1 start-all

# Check if services are running
.\scripts\dev.ps1 status

# Run linting
.\scripts\dev.ps1 ruff

# Clean Python cache files
.\scripts\dev.ps1 clean-cache

# Stop all services
.\scripts\dev.ps1 stop-all
```

#### Background Jobs

When using `start-all`, the API and Worker run as PowerShell background jobs. This allows the frontend to run in the foreground while other services run in the background.

**View job output:**
```powershell
# View all job output
Get-Job | Receive-Job -Keep

# View specific job
Receive-Job -Name "OpenNotebook-API" -Keep
```

**Manage jobs:**
```powershell
# List jobs
Get-Job

# Stop a specific job
Stop-Job -Name "OpenNotebook-API"

# Remove completed jobs
Get-Job | Remove-Job
```

#### Execution Policy

If you encounter "script execution is disabled" errors:

```powershell
# Allow scripts (recommended - run as Administrator)
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Or bypass for single execution
PowerShell -ExecutionPolicy Bypass -File .\scripts\dev.ps1 start-all
```

#### Troubleshooting

**Services not stopping:**
```powershell
# Force stop all
.\scripts\dev.ps1 stop-all

# If that doesn't work, force kill processes
Get-Process *python* | Stop-Process -Force
Get-Process *node* | Stop-Process -Force
```

**Can't find processes:**

The script uses `CommandLine` property which requires PowerShell to be run with appropriate permissions. If status checks fail:
- Run PowerShell as Administrator
- Check Task Manager manually
- Use `docker compose ps` to check Docker services

**Port conflicts:**

If ports 8502, 5055, or 8000 are in use:
```powershell
# Find what's using a port
netstat -ano | findstr :8502

# Kill by PID
taskkill /PID <PID> /F
```

---

## Linux/macOS

For Linux and macOS users, use the `Makefile` in the repository root instead:

```bash
# Show available commands
make help

# Start all services
make start-all

# Check status
make status
```

---

## export_docs.py

Consolidates markdown documentation files for use with ChatGPT or other platforms with file upload limits.

### What It Does

- Scans all subdirectories in the `docs/` folder
- For each subdirectory, combines all `.md` files (excluding `index.md` files)
- Creates one consolidated markdown file per subdirectory
- Saves all exported files to `doc_exports/` in the project root

### Usage

```bash
# Using Makefile (recommended)
make export-docs

# Or run directly with uv
uv run python scripts/export_docs.py

# Or run with standard Python
python scripts/export_docs.py
```

### Output

The script creates `doc_exports/` directory with consolidated files like:

- `getting-started.md` - All getting-started documentation
- `user-guide.md` - All user guide content
- `features.md` - All feature documentation
- `development.md` - All development documentation
- etc.

Each exported file includes:
- A main header with the folder name
- Section headers for each source file
- Source file attribution
- The complete content from each markdown file
- Visual separators between sections

### Example Output Structure

```markdown
# Getting Started

This document consolidates all content from the getting-started documentation folder.

---

## Installation

*Source: installation.md*

[Full content of installation.md]

---

## Quick Start

*Source: quick-start.md*

[Full content of quick-start.md]

---
```

### Notes

- The `doc_exports/` directory is gitignored and safe to regenerate anytime
- Index files (`index.md`) are automatically excluded
- Files are sorted alphabetically for consistent output
- The script handles subdirectories only (ignores files in the root `docs/` folder)

---

## Contributing

When adding new development scripts:

1. **Cross-platform support**: Consider creating equivalents for both PowerShell (Windows) and Bash/Make (Linux/macOS)
2. **Documentation**: Update this README with script usage
3. **Error handling**: Include proper error messages and exit codes
4. **Help text**: Add `--help` or `help` command support

## Related Documentation

- [Windows Setup Guide](../docs/getting-started/windows-setup.md) - Complete Windows installation guide
- [Development Guide](../docs/deployment/development.md) - Development setup for all platforms
- [Contributing Guide](../CONTRIBUTING.md) - How to contribute to Open Notebook
