# Quick Start - Development

Get Open Notebook running locally in 5 minutes.

## Prerequisites

- **uv** (package manager) — install: <https://docs.astral.sh/uv/getting-started/installation/>
  (uv provisions a compatible Python — the project needs **3.11 or 3.12**, not 3.13)
- **Node.js 18+** — <https://nodejs.org/>
- **Docker** (for SurrealDB)
- **Git**

> `make` is not required in this fork — use the `dev.*` launcher below.

## 1. Clone the Repository

```bash
git clone https://github.com/stefanini-applications/sai-notebook.git
cd sai-notebook

# (If contributing, fork on GitHub, clone your fork, then:)
# git remote add upstream https://github.com/stefanini-applications/sai-notebook.git
```

## 2. Start Everything (one command)

```bash
dev.bat        # Windows   (or: .\dev.ps1, or: uv run python dev.py)
./dev.sh       # Linux/macOS
```

The launcher creates `.env`, installs dependencies, and starts SurrealDB + API +
worker + frontend together with combined logs. Wait for the **"Open Notebook is up"**
banner. `Ctrl+C` stops everything; `dev.bat stop` / `./dev.sh stop` force-stops leftovers.

## 3. Verify Everything Works

- **Frontend**: <http://localhost:3000> → Open Notebook UI
- **API Docs**: <http://localhost:5055/docs> → interactive API documentation
- **Database**: SurrealDB on `localhost:8000`

**All three show up?** ✅ You're ready to develop!

For the manual, terminal-per-service setup, see [from-source installation](../1-INSTALLATION/from-source.md#manual-setup-what-the-launcher-does).

---

## Next Steps

- **First Issue?** Pick a [good first issue](https://github.com/stefanini-applications/sai-notebook/issues?q=label%3A%22good+first+issue%22)
- **Understand the code?** Read [Architecture Overview](architecture.md)
- **Make changes?** Follow [Contributing Guide](contributing.md)
- **Setup details?** See [Development Setup](development-setup.md)

---

## Troubleshooting

### "Port 5055 / 3000 / 8000 already in use"
```bash
# Stop the stack's processes + container
dev.bat stop      # Windows
./dev.sh stop     # Linux/macOS
```

### "Can't connect to SurrealDB"
```bash
# Check if SurrealDB is running
docker compose ps surrealdb

# Confirm .env points at localhost (not the docker hostname "surrealdb")
#   SURREAL_URL=ws://localhost:8000/rpc
```

### "Python version is too old"
```bash
# Let uv use a compatible interpreter (3.11–3.12)
uv sync --python 3.12
```

### "npm: command not found"
Install Node.js 18+ from <https://nodejs.org/>.

---

## Common Development Commands

```bash
# Run tests
uv run pytest

# Format code
ruff check . --fix

# Type checking
uv run python -m mypy .

# Run the full stack
./dev.sh          # or dev.bat on Windows
```

---

Need more help? See [Development Setup](development-setup.md) for details or join our [Discord](https://discord.gg/37XJPXfz2w).
