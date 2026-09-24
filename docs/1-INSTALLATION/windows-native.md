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

3. **Start the four services**, each in its own terminal, from the `open-notebook` folder.

   > Open Notebook does not ship a launcher script — start the services manually as below (or wrap them in your own `.bat`, see [Optional: one-click launcher](#optional-one-click-launcher)).

   ```batch
   REM Optional: point Open Notebook at a separate data folder (see Issue 4 below).
   REM Set this in each terminal before running, or skip to use ./data.
   set DATA_FOLDER=%USERPROFILE%\Projects\open-notebook-data

   REM Terminal 1 — SurrealDB
   surreal start --user root --pass root --bind 127.0.0.1:8000 rocksdb:%DATA_FOLDER%\surrealdb

   REM Terminal 2 — API
   uv run --env-file .env run_api.py

   REM Terminal 3 — Worker (module form avoids the Windows "canonicalize" error, see Issue 3)
   set PYTHONPATH=%CD%
   uv run --env-file .env python -m surreal_commands.cli.worker --import-modules commands

   REM Terminal 4 — Frontend
   cd frontend && npm run dev
   ```

4. **Open the app:** http://127.0.0.1:3000

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
└── start-open-notebook.bat  # Optional launcher you create yourself (see below)
```

**Why separate data folder?** Prevents accidental data loss when updating/reinstalling code.

## Optional: one-click launcher

Open Notebook does not ship a launcher, but you can save the following as
`start-open-notebook.bat` (anywhere you like) to start all four services with a
double-click. Adjust `ROOT` and `DATA_ROOT` to match your setup.

```batch
@echo off
REM --- adjust these two paths ---
set ROOT=%USERPROFILE%\Projects\open-notebook
set DATA_ROOT=%USERPROFILE%\Projects\open-notebook-data

set DATA_FOLDER=%DATA_ROOT%
set PYTHONPATH=%ROOT%
cd /d %ROOT%

start "SurrealDB" surreal start --user root --pass root --bind 127.0.0.1:8000 rocksdb:%DATA_ROOT%\surrealdb
start "API" cmd /k "uv run --env-file .env run_api.py"
start "Worker" cmd /k "uv run --env-file .env python -m surreal_commands.cli.worker --import-modules commands"
start "Frontend" cmd /k "cd /d %ROOT%\frontend && npm run dev"
```

Then open http://127.0.0.1:3000.

## Optional: production frontend build

`npm run dev` is the development server: it compiles pages on demand and runs
with development overhead, unlike what the Docker image runs. For day-to-day use you can build once and serve the
standalone output, which is exactly what the container does (`node server.js`):

```batch
cd frontend
npm run build

REM The standalone output does not include static assets — copy them in
REM (the Dockerfile does the same with COPY). Without this the UI loads unstyled.
xcopy .next\static .next\standalone\.next\static /E /I /Y
xcopy public .next\standalone\public /E /I /Y

cd .next\standalone
set PORT=8502
set HOSTNAME=127.0.0.1
node server.js
```

Then open http://127.0.0.1:8502. Re-run the build and both `xcopy` lines after
every upgrade.

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

Once running, add models in Manage → Models. Common model names:

| Provider  | Models                                                       |
| --------- | ------------------------------------------------------------ |
| OpenAI    | `gpt-4o`, `gpt-4o-mini`, `gpt-4-turbo`, `text-embedding-3-small` |
| Anthropic | `claude-sonnet-4-20250514`, `claude-3-5-sonnet-20241022`, `claude-3-5-haiku-20241022` |
| Google    | `gemini-3.5-flash`, `gemini-2.5-flash`, `gemini-2.5-pro`     |
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

## Migrating from a Docker Install

If you already run Open Notebook with the stock `docker-compose.yml`, you can
move to a native install **without re-importing anything**: the compose file
bind-mounts `./surreal_data` and `./notebook_data`, so the database and uploads
already live on your Windows disk.

Run the `docker compose` commands below from the folder that contains your
`docker-compose.yml`, so they work whatever your container names are.

1. **Match the SurrealDB version.** A native `surreal` of the same version can
   open the existing RocksDB files directly. Check the container's version:

   ```batch
   docker compose exec surrealdb /surreal version
   ```

   and download the matching Windows binary from the
   [SurrealDB releases](https://github.com/surrealdb/surrealdb/releases).

2. **Back up first** while the containers are still running:

   ```batch
   surreal export --endpoint http://127.0.0.1:8000 --username root --password <your-password> ^
     --namespace open_notebook --database open_notebook backup.surql
   ```

3. **Remove the containers.** Stopping is not enough: the stock compose file
   uses `restart: always`, so Docker Desktop would start them again on its next
   launch and they would fight the native services over ports 8000 and 5055.
   `down` removes the containers but keeps the bind-mounted `surreal_data` and
   `notebook_data` folders (do **not** add `-v`); `docker compose up -d` brings
   the Docker setup back if you need to roll back:

   ```batch
   docker compose down
   ```

4. **Start SurrealDB on the existing data** (path from the compose file's
   `rocksdb:/mydata/mydatabase.db`):

   ```batch
   surreal start --user root --pass <your-password> --bind 127.0.0.1:8000 rocksdb:surreal_data\mydatabase.db
   ```

5. **Fix what only made sense inside the container**, before starting the API
   and worker. Run these in `surreal sql` (namespace/database `open_notebook`):

   ```sql
   -- Credentials that reached host services (Ollama, local embedding servers)
   -- through host.docker.internal now run on the same machine:
   UPDATE credential SET base_url = string::replace(base_url, 'host.docker.internal', '127.0.0.1')
     WHERE base_url CONTAINS 'host.docker.internal';

   -- A job that was running when the container stopped stays 'running' forever;
   -- put it back in the queue (the worker picks up 'new' jobs on startup):
   UPDATE command SET status = 'new' WHERE status = 'running';
   ```

6. **Start the API, worker and frontend** as described above.

**Known limitation:** sources uploaded inside Docker store absolute container
paths such as `/app/data/uploads/<file>.pdf`, which do not resolve on Windows.
Their extracted text, notes and embeddings are unaffected — search and chat keep
working — but features that re-read the original file (re-processing, download)
will not find it for those older sources. New uploads are fine.

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
*Docker migration and production frontend build tested on Windows 11 x64 with Open Notebook v1.14.0 and SurrealDB 2.6.5*
*Created: January 2026*
