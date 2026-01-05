# Quick Start - Development

Get Open Notebook running locally in 5 minutes.

## Prerequisites

- **Python 3.11+**
- **Git**
- **uv** (package manager) - install with `curl -LsSf https://astral.sh/uv/install.sh | sh`
- **Docker** (optional, for SurrealDB)

## 1. Clone the Repository (2 min)

```bash
# Fork the repository on GitHub first, then clone your fork
git clone https://github.com/YOUR_USERNAME/open-notebook.git
cd open-notebook

# Add upstream remote for updates
git remote add upstream https://github.com/lfnovo/open-notebook.git
```

## 2. Install Dependencies (2 min)

```bash
# Install Python dependencies
uv sync

# Verify uv is working
uv --version
```

## 3. Start Services (1 min)

In separate terminal windows:

```bash
# Terminal 1: Start SurrealDB (database)
make database
# or: docker run -d --name surrealdb -p 8000:8000 surrealdb/surrealdb:v2 start --user root --pass password --bind 0.0.0.0:8000 memory

# Terminal 2: Start API (backend on port 5055)
make api
# or: uv run --env-file .env uvicorn api.main:app --host 0.0.0.0 --port 5055

# Terminal 3: Start Frontend (UI on port 3000)
cd frontend && npm run dev
```

## 4. Verify Everything Works (instant)

- **API Health**: http://localhost:5055/health → should return `{"status": "ok"}`
- **API Docs**: http://localhost:5055/docs → interactive API documentation
- **Frontend**: http://localhost:3000 → Open Notebook UI

**All three show up?** ✅ You're ready to develop!

---

## Next Steps

- **First Issue?** Pick a [good first issue](https://github.com/lfnovo/open-notebook/issues?q=label%3A%22good+first+issue%22)
- **Understand the code?** Read [Architecture Overview](architecture.md)
- **Make changes?** Follow [Contributing Guide](contributing.md)
- **Setup details?** See [Development Setup](development-setup.md)

---

## Troubleshooting

### "Port 5055 already in use"
```bash
# Find what's using the port
lsof -i :5055

# Use a different port
uv run uvicorn api.main:app --port 5056
```

### "Can't connect to SurrealDB"
```bash
# Check if SurrealDB is running
docker ps | grep surrealdb

# Restart it
make database
```

### "Python version is too old"
```bash
# Check your Python version
python --version  # Should be 3.11+

# Use Python 3.11 specifically
uv sync --python 3.11
```

### "npm: command not found"
```bash
# Install Node.js from https://nodejs.org/
# Then install frontend dependencies
cd frontend && npm install
```

---

## Common Development Commands

```bash
# Run tests
uv run pytest

# Format code
make ruff

# Type checking
make lint

# Run the full stack
make start-all

# View API documentation
open http://localhost:5055/docs
```

---

Need more help? See [Development Setup](development-setup.md) for details or join our [Discord](https://discord.gg/37XJPXfz2w).
