# From Source Installation

Clone the repository and run locally. **For developers and contributors.**

## Prerequisites

- **Python 3.11+** - [Download](https://www.python.org/)
- **Node.js 18+** - [Download](https://nodejs.org/)
- **Git** - [Download](https://git-scm.com/)
- **Docker** (for SurrealDB) - [Download](https://docker.com/)
- **uv** (Python package manager) - `curl -LsSf https://astral.sh/uv/install.sh | sh`
- API key from OpenAI or similar (or use Ollama for free)

## Quick Setup (10 minutes)

### 1. Clone Repository

```bash
git clone https://github.com/lfnovo/open-notebook.git
cd open-notebook

# If you forked it:
git clone https://github.com/YOUR_USERNAME/open-notebook.git
cd open-notebook
git remote add upstream https://github.com/lfnovo/open-notebook.git
```

### 2. Install Python Dependencies

```bash
uv sync
uv pip install python-magic
```

#### 2.1 Alternative: Conda Setup (Optional)

If you prefer using **Conda** to manage your environments, follow these steps instead of the standard `uv sync`:

```bash
# Create and activate the environment
conda create -n open-notebook python=3.11 -y
conda activate open-notebook

# Install uv inside conda to maintain compatibility with the Makefile
conda install -c conda-forge uv nodejs -y

# Sync dependencies
uv sync
```

> **Note**: Installing `uv` inside your Conda environment ensures that commands like `make start-all` and `make api` continue to work seamlessly.

### 3. Start SurrealDB

```bash
# Terminal 1
make database
# or: docker compose up surrealdb
```

### 4. Set Environment Variables

```bash
cp .env.example .env
# Edit .env and add your API key:
# OPENAI_API_KEY=sk-...
# (or ANTHROPIC_API_KEY, GROQ_API_KEY, etc.)
```

### 5. Start API

```bash
# Terminal 2
make api
# or: uv run --env-file .env uvicorn api.main:app --host 0.0.0.0 --port 5055
```

### 6. Start Frontend

```bash
# Terminal 3
cd frontend && npm install && npm run dev
```

### 7. Access

- **Frontend**: http://localhost:3000
- **API Docs**: http://localhost:5055/docs
- **Database**: http://localhost:8000

---

## Development Workflow

### Code Quality

```bash
# Format and lint Python
make ruff
# or: ruff check . --fix

# Type checking
make lint
# or: uv run python -m mypy .
```

### Run Tests

```bash
uv run pytest tests/
```

### Common Commands

```bash
# Start everything
make start-all

# View API docs
open http://localhost:5055/docs

# Check database migrations
# (Auto-run on API startup)

# Clean up
make clean
```

---

## Troubleshooting

### Python version too old

```bash
python --version  # Check version
uv sync --python 3.11  # Use specific version
```

### npm: command not found

Install Node.js from https://nodejs.org/

### Database connection errors

```bash
docker ps  # Check SurrealDB running
docker logs surrealdb  # View logs
```

### Port 5055 already in use

```bash
# Use different port
uv run uvicorn api.main:app --port 5056
```

---

## Next Steps

1. Read [Development Guide](../7-DEVELOPMENT/quick-start.md)
2. See [Architecture Overview](../7-DEVELOPMENT/architecture.md)
3. Check [Contributing Guide](../7-DEVELOPMENT/contributing.md)

---

## Getting Help

- **Discord**: [Community](https://discord.gg/37XJPXfz2w)
- **Issues**: [GitHub Issues](https://github.com/lfnovo/open-notebook/issues)
