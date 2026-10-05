# From Source Installation

Clone the repository and run each part yourself. **For developers and contributors.** To just use Open Notebook, [Docker Compose](docker-compose.md) is simpler.

A source install runs four processes, each in its own terminal:

| Process | Command | Port |
|---|---|---|
| SurrealDB (in Docker) | `make database` | 8000 |
| API | `make api` | 5055 |
| Background worker | `make worker` | none |
| Frontend (Next.js dev server) | `npm run dev` in `frontend/` | 3000 |

## Prerequisites

- **Python 3.11 or 3.12.** 3.13 and later are not supported yet (`pyproject.toml` requires `>=3.11,<3.13`). uv can install a matching Python for you.
- **uv**: `curl -LsSf https://astral.sh/uv/install.sh | sh` ([other install methods](https://docs.astral.sh/uv/getting-started/installation/))
- **Node.js 20.9 or later** (22 LTS recommended; CI uses 22). Next.js 16 refuses older versions.
- **Git**
- **Docker**, to run SurrealDB
- **ffmpeg**, for audio and video sources and podcasts (`brew install ffmpeg`, `sudo apt install ffmpeg`, or `winget install Gyan.FFmpeg`)

## 1. Clone the repository

```bash
git clone https://github.com/lfnovo/open-notebook.git
cd open-notebook
```

If you plan to contribute, clone your fork instead and add `upstream`:

```bash
git clone https://github.com/YOUR_USERNAME/open-notebook.git
cd open-notebook
git remote add upstream https://github.com/lfnovo/open-notebook.git
```

## 2. Install Python dependencies

```bash
uv sync
```

<details>
<summary>Using Conda instead</summary>

```bash
conda create -n open-notebook python=3.12 -y
conda activate open-notebook
conda install -c conda-forge uv nodejs -y
uv sync
```

Installing `uv` inside the Conda environment keeps the `make` targets working.
</details>

## 3. Create your `.env`

```bash
cp .env.example .env
```

Edit `.env` and change two lines:

```env
OPEN_NOTEBOOK_ENCRYPTION_KEY=any-long-random-secret
SURREAL_URL=ws://localhost:8000/rpc
```

The example file points `SURREAL_URL` at `surrealdb`, a host name that only exists inside Docker Compose. A process running on your machine reaches the database at `localhost`.

## 4. Start SurrealDB

```bash
make database
```

This runs `docker compose up -d surrealdb` with the repository's `docker-compose.yml`. Docker Compose reads `SURREAL_USER` and `SURREAL_PASSWORD` from your `.env`, so the database and the API use the same credentials.

## 5. Start the API

```bash
# Terminal 2
make api
```

The API listens on `http://localhost:5055` and runs database migrations on startup. Interactive API docs: http://localhost:5055/docs.

## 6. Start the worker

```bash
# Terminal 3
make worker
```

Source processing, embeddings, insights and podcasts run as background jobs that this worker picks up. Without it, new sources stay queued forever.

## 7. Start the frontend

```bash
# Terminal 4
cd frontend
npm install
npm run dev
```

Open **http://localhost:3000**.

## 8. Connect a provider

Follow [Connect a provider](../4-AI-PROVIDERS/index.md#connect-a-provider). It ends with a test chat. Chat won't work until the default models are set.

If you use Ollama on the same machine, its base URL is `http://localhost:11434`; there is no container in between.

---

## Development commands

```bash
uv run pytest tests/          # tests
make ruff                     # ruff check . --fix
uv run ruff format .          # format
make lint                     # mypy
make clean-cache              # remove __pycache__, .mypy_cache, etc.
```

The development workflow is described in the [Development Setup](../7-DEVELOPMENT/development-setup.md) guide.

---

## Troubleshooting

**Wrong Python version.** `uv sync --python 3.12` installs and uses a supported version.

**`npm run dev` fails with an engine or syntax error.** Your Node.js is older than 20.9. Check with `node --version`.

**API can't connect to the database.** Check that `SURREAL_URL` in `.env` uses `localhost`, and that the database is running: `docker compose ps` and `docker compose logs surrealdb`.

**Sources stay queued.** The worker isn't running, or it crashed; check its terminal.

**Port 5055 already in use.** Something else is on that port. Set `API_PORT` in `.env` to move the API; the frontend then needs `API_URL=http://localhost:<port>` in its environment (for example in `frontend/.env.local`).

---

## Next steps

- [Development quick start](../7-DEVELOPMENT/quick-start.md)
- [Architecture](../7-DEVELOPMENT/architecture.md)
- [Contributing](../7-DEVELOPMENT/contributing.md)

**Need help?** [Discord](https://discord.gg/37XJPXfz2w) · [GitHub Issues](https://github.com/lfnovo/open-notebook/issues)
