# Local Development Setup

This guide walks you through setting up Open Notebook for local development. Follow these steps to get the full stack running on your machine.

## Prerequisites

Before you start, ensure you have the following installed:

- **Python 3.11+** - Check with: `python --version`
- **uv** (recommended) or **pip** - Install from: https://github.com/astral-sh/uv
- **SurrealDB** - Via Docker or binary (see below)
- **Docker** (optional) - For containerized database
- **Node.js 18+** (optional) - For frontend development
- **Git** - For version control

## Step 1: Clone and Initial Setup

```bash
# Clone the repository
git clone https://github.com/lfnovo/open-notebook.git
cd open-notebook

# Add upstream remote for keeping your fork updated
git remote add upstream https://github.com/lfnovo/open-notebook.git
```

## Step 2: Install Python Dependencies

```bash
# Using uv (recommended)
uv sync

# Or using pip
pip install -e .
```

## Step 3: Environment Variables

Create a `.env` file in the project root with your configuration:

```bash
# Copy from example
cp .env.example .env
```

Edit `.env` with your settings:

```bash
# Database
SURREAL_URL=ws://localhost:8000/rpc
SURREAL_USER=root
SURREAL_PASSWORD=password
SURREAL_NAMESPACE=open_notebook
SURREAL_DATABASE=development

# AI Providers (add your API keys)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=AI...
GROQ_API_KEY=gsk-...

# Application
APP_PASSWORD=  # Optional password protection
DEBUG=true
LOG_LEVEL=DEBUG
```

### AI Provider Keys

You'll need at least one AI provider. Popular options:

- **OpenAI** - https://platform.openai.com/api-keys
- **Anthropic (Claude)** - https://console.anthropic.com/
- **Google** - https://ai.google.dev/
- **Groq** - https://console.groq.com/

For local development, you can also use:
- **Ollama** - Run locally without API keys (see "Local Ollama" below)

## Step 4: Start SurrealDB

### Option A: Using Docker (Recommended)

```bash
# Start SurrealDB in memory
docker run -d --name surrealdb -p 8000:8000 \
  surrealdb/surrealdb:v2 start \
  --user root --pass password \
  --bind 0.0.0.0:8000 memory

# Or with persistent storage
docker run -d --name surrealdb -p 8000:8000 \
  -v surrealdb_data:/data \
  surrealdb/surrealdb:v2 start \
  --user root --pass password \
  --bind 0.0.0.0:8000 file:/data/surreal.db
```

### Option B: Using Make

```bash
make database
```

### Option C: Using Docker Compose

```bash
docker compose up -d surrealdb
```

### Verify SurrealDB is Running

```bash
# Should show server information
curl http://localhost:8000/
```

## Step 5: Run Database Migrations

Database migrations run automatically when you start the API. The first startup will apply any pending migrations.

To verify migrations manually:

```bash
# API will run migrations on startup
uv run python -m api.main
```

Check the logs - you should see messages like:
```
Running migration 001_initial_schema
Running migration 002_add_vectors
...
Migrations completed successfully
```

## Step 6: Start the API Server

In a new terminal window:

```bash
# Terminal 2: Start API (port 5055)
uv run --env-file .env uvicorn api.main:app --host 0.0.0.0 --port 5055

# Or using the shortcut
make api
```

You should see:
```
INFO:     Application startup complete
INFO:     Uvicorn running on http://0.0.0.0:5055
```

### Verify API is Running

```bash
# Check health endpoint
curl http://localhost:5055/health

# View API documentation
open http://localhost:5055/docs
```

## Step 7: Start the Frontend (Optional)

If you want to work on the frontend, start Next.js in another terminal:

```bash
# Terminal 3: Start Next.js frontend (port 3000)
cd frontend
npm install  # First time only
npm run dev
```

You should see:
```
> next dev
  ▲ Next.js 16.x
  - Local:        http://localhost:3000
```

### Access the Frontend

Open your browser to: http://localhost:3000

## Verification Checklist

After setup, verify everything is working:

- [ ] **SurrealDB**: `curl http://localhost:8000/` returns content
- [ ] **API**: `curl http://localhost:5055/health` returns `{"status": "ok"}`
- [ ] **API Docs**: `open http://localhost:5055/docs` works
- [ ] **Database**: API logs show migrations completing
- [ ] **Frontend** (optional): `http://localhost:3000` loads

## Starting Services Together

### Quick Start All Services

```bash
make start-all
```

This starts SurrealDB, API, and frontend in one command.

### Individual Terminals (Recommended for Development)

**Terminal 1 - Database:**
```bash
make database
```

**Terminal 2 - API:**
```bash
make api
```

**Terminal 3 - Frontend:**
```bash
cd frontend && npm run dev
```

## Development Tools Setup

### Pre-commit Hooks (Optional but Recommended)

Install git hooks to automatically check code quality:

```bash
uv run pre-commit install
```

Now your commits will be checked before they're made.

### Code Quality Commands

```bash
# Lint Python code (auto-fix)
make ruff
# or: ruff check . --fix

# Type check Python code
make lint
# or: uv run python -m mypy .

# Run tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=open_notebook
```

## Common Development Tasks

### Running Tests

```bash
# Run all tests
uv run pytest

# Run specific test file
uv run pytest tests/test_notebooks.py

# Run with coverage report
uv run pytest --cov=open_notebook --cov-report=html
```

### Creating a Feature Branch

```bash
# Create and switch to new branch
git checkout -b feature/my-feature

# Make changes, then commit
git add .
git commit -m "feat: add my feature"

# Push to your fork
git push origin feature/my-feature
```

### Updating from Upstream

```bash
# Fetch latest changes
git fetch upstream

# Rebase your branch
git rebase upstream/main

# Push updated branch
git push origin feature/my-feature -f
```

## Troubleshooting

### "Connection refused" on SurrealDB

**Problem**: API can't connect to SurrealDB

**Solutions**:
1. Check if SurrealDB is running: `docker ps | grep surrealdb`
2. Verify URL in `.env`: Should be `ws://localhost:8000/rpc`
3. Restart SurrealDB: `docker stop surrealdb && docker rm surrealdb`
4. Then restart with: `docker run -d --name surrealdb -p 8000:8000 surrealdb/surrealdb:v2 start --user root --pass password --bind 0.0.0.0:8000 memory`

### "Address already in use"

**Problem**: Port 5055 or 3000 is already in use

**Solutions**:
```bash
# Find process using port
lsof -i :5055  # Check port 5055

# Kill process (macOS/Linux)
kill -9 <PID>

# Or use different port
uvicorn api.main:app --port 5056
```

### Module not found errors

**Problem**: Import errors when running API

**Solutions**:
```bash
# Reinstall dependencies
uv sync

# Or with pip
pip install -e .
```

### Database migration failures

**Problem**: API fails to start with migration errors

**Solutions**:
1. Check SurrealDB is running: `curl http://localhost:8000/`
2. Check credentials in `.env` match your SurrealDB setup
3. Check logs for specific migration error: `make api 2>&1 | grep -i migration`
4. Verify database exists: Check SurrealDB console at http://localhost:8000/

### Migrations not applying

**Problem**: Database schema seems outdated

**Solutions**:
1. Restart API - migrations run on startup: `make api`
2. Check logs show "Migrations completed successfully"
3. Verify `/migrations/` folder exists and has files
4. Check SurrealDB is writable and not in read-only mode

## Optional: Local Ollama Setup

For testing with local AI models:

```bash
# Install Ollama from https://ollama.ai

# Pull a model (e.g., Mistral 7B)
ollama pull mistral

# Add to .env
OLLAMA_BASE_URL=http://localhost:11434
```

Then in your code, you can use Ollama through the Esperanto library.

## Optional: Docker Development Environment

Run entire stack in Docker:

```bash
# Start all services
docker compose --profile multi up

# Logs
docker compose logs -f

# Stop services
docker compose down
```

## Next Steps

After setup is complete:

1. **Read the Contributing Guide** - [contributing.md](contributing.md)
2. **Explore the Architecture** - Check the documentation
3. **Find an Issue** - Look for "good first issue" on GitHub
4. **Set Up Pre-commit** - Install git hooks for code quality
5. **Join Discord** - https://discord.gg/37XJPXfz2w

## Getting Help

If you get stuck:

- **Discord**: [Join our server](https://discord.gg/37XJPXfz2w) for real-time help
- **GitHub Issues**: Check existing issues for similar problems
- **GitHub Discussions**: Ask questions in discussions
- **Documentation**: See [code-standards.md](code-standards.md) and [testing.md](testing.md)

---

**Ready to contribute?** Go to [contributing.md](contributing.md) for the contribution workflow.
