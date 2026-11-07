# Windows Native Installation (No Docker)

This guide runs [Open Notebook](https://github.com/lfnovo/open-notebook) on Windows **natively, without Docker or WSL**. It is community-maintained; the officially supported route is [Docker Compose](docker-compose.md).

## Who Is This For?

- **Windows ARM64 users**: Docker Desktop and WSL2 have limitations on ARM64
- **Users without Hyper-V**: some Windows editions can't run Docker Desktop
- **Users who prefer native installs**: fewer layers, easier debugging

## Prerequisites

| Software | Installation | Notes |
| --- | --- | --- |
| Git | `winget install Git.Git` | |
| uv | `winget install astral-sh.uv` | Also installs a matching Python for you |
| Python 3.11 or 3.12 | Installed by `uv sync` | 3.13+ is not supported yet |
| Node.js 20.9+ | `winget install OpenJS.NodeJS.LTS` | Next.js 16 requires 20.9 or later |
| SurrealDB 2.x | [SurrealDB releases](https://github.com/surrealdb/surrealdb/releases) or `scoop install surrealdb` | Use a 2.x release: the Docker setup pins `surrealdb:v2` |
| ffmpeg | `winget install Gyan.FFmpeg` | Needed for audio/video sources and podcasts |

## Quick Start

1. **Clone and install:**

   ```batch
   cd %USERPROFILE%\Projects
   git clone https://github.com/lfnovo/open-notebook.git
   cd open-notebook
   uv sync
   cd frontend && npm install && cd ..
   ```

2. **Create `.env`:** generate an encryption key with

   ```batch
   uv run python -c "import secrets; print(secrets.token_hex(32))"
   ```

   then copy `.env.example` to `.env` and change these two lines, pasting the generated value as the key (never an example value). Keep it: if it changes, saved API keys can't be decrypted.

   ```env
   OPEN_NOTEBOOK_ENCRYPTION_KEY=<the value you generated>
   SURREAL_URL="ws://127.0.0.1:8000/rpc"
   ```

   Use `127.0.0.1`, not `localhost` and not `surrealdb` (see [Issue 2](#issue-2-database-health-check-timeout)). You add AI provider keys in the UI later, not in `.env`.

3. **Start the four services**, each in its own terminal, from the `open-notebook` folder.

   > Open Notebook does not ship a launcher script. Start the services manually as below, or wrap them in your own `.bat` (see [Optional: one-click launcher](#optional-one-click-launcher)).

   ```batch
   REM Terminal 1 — SurrealDB (database files go in the folder you name here)
   surreal start --user root --pass root --bind 127.0.0.1:8000 "rocksdb:%USERPROFILE%\Projects\open-notebook-data\surrealdb"

   REM Terminal 2 — API
   uv run --env-file .env run_api.py

   REM Terminal 3 — Worker (module form avoids the Windows "canonicalize" error, see Issue 3)
   set PYTHONPATH=%CD%
   uv run --env-file .env python -m surreal_commands.cli.worker --import-modules commands

   REM Terminal 4 — Frontend
   cd frontend && npm run dev
   ```

4. **Open the app** at http://127.0.0.1:3000.

5. **Connect a provider:** follow [Connect a provider](../4-AI-PROVIDERS/index.md#connect-a-provider). It ends with a test chat; chat won't work until the default models are set. A local Ollama is at `http://127.0.0.1:11434`.

## Where your data lives

- **Database:** the folder you pass to `surreal start` (above: `%USERPROFILE%\Projects\open-notebook-data\surrealdb`). Keeping it outside the code folder protects it when you reinstall.
- **Uploads and chat checkpoints:** always in the `data\` folder inside `open-notebook\`. The path is fixed in `open_notebook/config.py` and can't be changed with an environment variable. Back it up together with the database.

## Optional: one-click launcher

Open Notebook does not ship a launcher, but you can save the following as
`start-open-notebook.bat` (anywhere you like) to start all four services with a
double-click. Adjust `ROOT` and `DB_DIR` to match your setup.

```batch
@echo off
REM --- adjust these two paths ---
set ROOT=%USERPROFILE%\Projects\open-notebook
set DB_DIR=%USERPROFILE%\Projects\open-notebook-data\surrealdb

set PYTHONPATH=%ROOT%
cd /d %ROOT%

start "SurrealDB" surreal start --user root --pass root --bind 127.0.0.1:8000 "rocksdb:%DB_DIR%"
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
   surreal start --user root --pass <your-password> --bind 127.0.0.1:8000 "rocksdb:surreal_data\mydatabase.db"
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

- Verify the API is running: http://127.0.0.1:5055/docs
- Open the UI at `http://127.0.0.1:3000`. The frontend derives the API address from the address you use (`http://127.0.0.1:5055`), and the API only listens on `127.0.0.1` by default.

### Worker not processing commands

- Check the Worker window for errors
- Verify `PYTHONPATH` is set to the `open-notebook` folder in that terminal

## Contributing

Found another Windows-specific issue? Please share your solution!

---

*Tested on Windows 11 ARM64 with Open Notebook v1.6.0*
*Docker migration and production frontend build tested on Windows 11 x64 with Open Notebook v1.14.0 and SurrealDB 2.6.5*
*Created: January 2026*
