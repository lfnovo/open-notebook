# Open Notebook Windows Installation Guide (Native, No Docker)

This guide documents how to install and run [Open Notebook](https://github.com/lfnovo/open-notebook) on Windows **natively without Docker or WSL**.

## Who Is This For?

- **Windows ARM64 users** - Docker Desktop and WSL2 have limitations on ARM64
- **Users without Hyper-V** - Some Windows editions don't support Docker
- **Users who prefer native installs** - Simpler architecture, easier debugging

## What This Guide Covers

- Native Windows installation steps
- Critical configuration fixes for Windows
- Troubleshooting common issues
- Upgrade and maintenance scripts

## Prerequisites

| Software     | Installation                     | Required |
| ------------ | -------------------------------- | -------- |
| Git          | `winget install Git.Git`         | Yes      |
| Python 3.12+ | Via uv (installed automatically) | Yes      |
| Node.js 18+  | `winget install OpenJS.NodeJS`   | Yes      |
| uv           | `pip install uv`                 | Yes      |
| SurrealDB    | `scoop install surrealdb`        | Yes      |

## Quick Start

1. **Clone and setup:**

   ```bash
   cd %USERPROFILE%\Projects  # or your preferred location
   git clone https://github.com/lfnovo/open-notebook.git
   cd open-notebook
   uv sync
   cd frontend && npm install && cd ..
   ```

2. **Configure `.env`:**

   - Copy `.env.example` to `.env`

   - Add your API keys

   - **CRITICAL:** Change `SURREAL_URL` from `localhost` to `127.0.0.1`:

     ```env
     SURREAL_URL="ws://127.0.0.1:8000/rpc"
     ```

3. **Edit `start-open-notebook.bat`:**

   - Update `ROOT` and `DATA_ROOT` paths to match your setup
   - Place in parent directory of `open-notebook`

4. **Run:** Double-click `start-open-notebook.bat`

## Directory Structure (Recommended)

```
YourProjectsFolder\
├── open-notebook\           # Source code (git clone)
│   ├── .venv\               # Python virtual environment (created by uv)
│   ├── frontend\            # Next.js frontend
│   ├── commands\            # Worker command modules
│   └── .env                 # Your configuration
├── open-notebook-data\      # Data storage (SEPARATE from code!)
│   ├── surrealdb\           # Database files
│   ├── uploads\             # Uploaded documents
│   └── sqlite-db\           # LangGraph checkpoints
└── start-open-notebook.bat  # Launcher script
```

**Why separate data folder?** Prevents accidental data loss when updating/reinstalling code.

## Critical Windows Fixes

### Issue 1: Wrong Python Version

**Symptom:**

```
ModuleNotFoundError: No module named 'langgraph.checkpoint.sqlite'
```

Traceback shows system Python (e.g., `C:\Python314\`) instead of venv.

**Cause:** Windows may have multiple Python versions. The venv's `activate.bat` doesn't always override correctly.

**Solution:** Use `uv run` instead of direct python calls:

```batch
REM Wrong:
.venv\Scripts\python.exe run_api.py

REM Correct:
uv run python run_api.py
```

### Issue 2: Database Health Check Timeout

**Symptom:**

```
WARNING: Database health check timed out after 2 seconds
```

Frontend shows "Database is offline" even though SurrealDB is running.

**Cause:** `.env` uses `localhost` but SurrealDB binds to `127.0.0.1`.

**Solution:** In `.env`, change:

```env
# Wrong:
SURREAL_URL="ws://localhost:8000/rpc"

# Correct:
SURREAL_URL="ws://127.0.0.1:8000/rpc"
```

### Issue 3: Worker "Failed to canonicalize script path"

**Symptom:**

```
Failed to canonicalize script path
```

**Cause:** The `surreal-commands-worker.exe` can't find the Python `commands` module.

**Solution:** Use Python module invocation with PYTHONPATH:

```batch
set PYTHONPATH=%ROOT%
uv run --env-file .env python -m surreal_commands.cli.worker --import-modules commands
```

### Issue 4: DATA_FOLDER Path Parsing Error

**Symptom:**

```
warning: Failed to parse environment file .env at position X
```

**Cause:** `uv` can't parse Windows paths with backslashes in `.env`.

**Solution:** Keep `DATA_FOLDER` **commented out** in `.env`. Set it via batch file:

```batch
set DATA_FOLDER=C:\path\to\open-notebook-data
```

## Configuration Files

### Modifying `open_notebook/config.py`

The default `config.py` uses a hardcoded data path. Modify it to read from environment:

```python
import os

# ROOT DATA FOLDER - can be overridden via DATA_FOLDER environment variable
DATA_FOLDER = os.environ.get("DATA_FOLDER", "./data")

# Rest of file uses DATA_FOLDER...
```

### Required `.env` Settings

```env
# Database - MUST use 127.0.0.1!
SURREAL_URL="ws://127.0.0.1:8000/rpc"
SURREAL_USER="root"
SURREAL_PASSWORD="root"
SURREAL_NAMESPACE="open_notebook"
SURREAL_DATABASE="open_notebook"

# API Keys (uncomment and fill in)
OPENAI_API_KEY=your-key-here
ANTHROPIC_API_KEY=your-key-here
GOOGLE_API_KEY=your-key-here
```

## Available AI Models

Once running, add models in Settings. Common model names:

| Provider  | Models                                                       |
| --------- | ------------------------------------------------------------ |
| OpenAI    | `gpt-4o`, `gpt-4o-mini`, `gpt-4-turbo`, `text-embedding-3-small` |
| Anthropic | `claude-sonnet-4-20250514`, `claude-3-5-sonnet-20241022`, `claude-3-5-haiku-20241022` |
| Google    | `gemini-2.0-flash`, `gemini-1.5-pro`, `gemini-1.5-flash`     |
| DeepSeek  | `deepseek-chat`, `deepseek-reasoner`                         |

## Upgrading

When a new version is released:

```batch
cd open-notebook
git pull
uv sync
cd frontend && npm install && cd ..
```

Then restart all services. Your `.env` and data are preserved.

## Services & Ports

| Service   | Port | URL                        |
| --------- | ---- | -------------------------- |
| SurrealDB | 8000 | ws://127.0.0.1:8000        |
| API       | 5055 | http://127.0.0.1:5055/docs |
| Frontend  | 3000 | http://127.0.0.1:3000      |

## Troubleshooting

### Services won't start

- Check if ports are in use: `netstat -ano | findstr :8000`
- Kill existing processes: `taskkill /F /PID <pid>`

### Frontend can't connect to API

- Verify API is running: http://127.0.0.1:5055/docs
- Check `.env` has `API_URL=http://localhost:5055`

### Worker not processing commands

- Check Worker window for errors
- Verify PYTHONPATH is set in startup script

## Contributing

Found another Windows-specific issue? Please share your solution!

---

*Tested on Windows 11 ARM64 with Open Notebook v1.6.0*
*Created: January 2026*
