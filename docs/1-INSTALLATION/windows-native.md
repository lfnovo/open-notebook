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
| SurrealDB 2.x | Install a local SurrealDB v2 binary | Yes   |

> **Important:** current `main` still uses the same SurrealDB `v2` migration syntax pinned in the repo's Docker files. A native install against SurrealDB `v3` currently fails on startup with `FLEXIBLE must be specified after TYPE`.

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

3. **Start SurrealDB 2.x separately**

   - Use a local SurrealDB v2 instance that listens on `127.0.0.1:8000`
   - Keep the credentials aligned with your `.env`
   - If you installed SurrealDB 3.x, downgrade to 2.x before continuing

4. **Start the API from the repo root:**

   ```batch
   uv run --env-file .env uvicorn api.main:app --host 127.0.0.1 --port 5055
   ```

5. **Start the frontend in a second terminal:**

   ```batch
   cd frontend
   npm run dev
   ```

6. **Open the app:**

   - Frontend: `http://127.0.0.1:3000`
   - API docs: `http://127.0.0.1:5055/docs`

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
uv run --env-file .env uvicorn api.main:app --host 127.0.0.1 --port 5055
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

### Issue 3: SurrealDB 3.x startup failure

**Symptom:**

```
Parse error: FLEXIBLE must be specified after TYPE
```

**Cause:** the current migration files still target the SurrealDB 2.x syntax used by the repo's Docker setup.

**Solution:** Run Open Notebook against SurrealDB 2.x for now.

### Issue 4: `DATA_ROOT` / `DATA_FOLDER` confusion

**Symptom:** Docs or local notes refer to `DATA_ROOT` or a `.env`-driven `DATA_FOLDER`, but the app still writes to the default repo-local `./data` path.

**Cause:** on current `main`, [`open_notebook/config.py`](../../open_notebook/config.py) sets `DATA_FOLDER = "./data"` directly. There is no supported `DATA_ROOT` environment variable in the source tree.

**Solution:** Leave the default `./data` location in place unless you are intentionally patching the code yourself.

## Configuration Files

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

## Contributing

Found another Windows-specific issue? Please share your solution!

---

*Tested on Windows 11 ARM64 with Open Notebook v1.6.0*
*Created: January 2026*
