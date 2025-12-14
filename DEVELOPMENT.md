# Development Guide

## Quick Start

### Option 1: Full Docker Development (Recommended for Backend)

```bash
# Start all services
docker-compose -f docker-compose.dev.yml up -d

# View logs
docker-compose -f docker-compose.dev.yml logs -f open_notebook

# Restart after config changes
docker-compose -f docker-compose.dev.yml restart open_notebook
```

**Access:**
- Frontend: http://localhost:8502
- API: http://localhost:5055/docs
- Ollama: http://localhost:11434

### Option 2: Hybrid Development (Best Hot Reload)

Run backend in Docker, frontend natively:

```bash
# Terminal 1: Start backend services
docker-compose -f docker-compose.dev.yml up surrealdb ollama whisper piper

# Terminal 2: Run API manually
cd /path/to/open-notebook
uv run uvicorn api.main:app --host 0.0.0.0 --port 5055 --reload

# Terminal 3: Run frontend with hot reload
cd frontend
npm run dev
# Access at http://localhost:3000
```

## Hot Reload Behavior

### ✅ What Works

**Backend (API & Worker):**
- ✅ Python file changes auto-reload (Uvicorn `--reload`)
- ✅ Changes reflected immediately
- ✅ Works perfectly in Docker on all platforms

**Frontend in Docker:**
- ✅ File changes sync to container
- ✅ TypeScript/React code updates
- ✅ Tailwind CSS changes apply
- ❌ **Browser auto-refresh DOES NOT work**

### ⚠️ Known Limitation: Docker + Windows/macOS File Watching

**Issue:**
Next.js Fast Refresh requires file system change events (inotify on Linux). Docker volume mounts on Windows (even with WSL2) and macOS don't reliably propagate these events from host to container.

**What This Means:**
- You edit `page.tsx` in VS Code
- File is saved and immediately synced to Docker container
- Next.js dev server doesn't detect the change
- Browser doesn't auto-refresh

**Workaround:**
1. Make your changes in VS Code
2. Save the file (Ctrl+S / Cmd+S)
3. **Manually refresh browser** (Ctrl+R / Cmd+R or F5)
4. Changes appear immediately

**This is a Docker limitation, not a bug in the setup.**

### 🔧 Configuration

We've enabled polling to maximize compatibility:

```bash
# In supervisord.conf
CHOKIDAR_USEPOLLING="true"      # Enable polling for file changes
CHOKIDAR_INTERVAL="100"         # Poll every 100ms
WATCHPACK_POLLING="true"        # Webpack/Turbopack polling
```

Polling helps but doesn't guarantee instant detection on all platforms.

## Development Workflows

### Frontend Development with Hot Reload

**Recommended: Native Next.js**

```bash
# One-time setup
cd frontend
npm install

# Every development session
npm run dev
# Open http://localhost:3000
# Full Fast Refresh works!
```

Update `.env.local`:
```bash
NEXT_PUBLIC_API_URL=http://localhost:5055/api
```

### Full-Stack Development

**Option A: Docker + Manual Refresh (Simple)**
- Use `docker-compose.dev.yml`
- Edit files in VS Code
- Manual browser refresh
- Perfect for API-heavy work

**Option B: Hybrid Setup (Best DX)**
- Backend in Docker
- Frontend native
- Full hot reload
- Slightly more complex setup

### Backend-Only Development

```bash
# Start everything
docker-compose -f docker-compose.dev.yml up -d

# Watch API logs
docker-compose -f docker-compose.dev.yml logs -f open_notebook | grep -i uvicorn

# Python changes auto-reload!
```

## Common Tasks

### Clear Next.js Cache

```bash
# Inside container
docker exec open-notebook-open_notebook-1 rm -rf /app/frontend/.next
docker-compose -f docker-compose.dev.yml restart open_notebook

# Native
cd frontend
rm -rf .next
npm run dev
```

### Install New Dependencies

**Python:**
```bash
# Add to pyproject.toml, then:
docker-compose -f docker-compose.dev.yml build open_notebook
docker-compose -f docker-compose.dev.yml up -d
```

**Frontend:**
```bash
# Inside container
docker exec open-notebook-open_notebook-1 sh -c "cd /app/frontend && npm install <package>"
docker-compose -f docker-compose.dev.yml restart open_notebook

# Native
cd frontend
npm install <package>
```

### Database Migrations

```bash
# Run migrations
docker exec open-notebook-open_notebook-1 uv run surreal-migrate apply

# Create new migration
docker exec open-notebook-open_notebook-1 uv run surreal-migrate create <name>
```

### Ollama Model Management

```bash
# Pull models
docker exec open-notebook-ollama-1 ollama pull qwen2.5:3b
docker exec open-notebook-ollama-1 ollama pull mxbai-embed-large

# List installed
docker exec open-notebook-ollama-1 ollama list
```

## Troubleshooting

### Frontend Not Updating

**Symptom:** Code changes don't appear in browser

**Solution:**
1. Verify file saved in VS Code
2. **Refresh browser manually** (Ctrl+R)
3. If still old: Clear .next cache (see above)
4. Check Docker logs for errors:
   ```bash
   docker-compose -f docker-compose.dev.yml logs --tail=50 open_notebook
   ```

### Port Already in Use

```bash
# Find process using port
netstat -ano | findstr :8502

# Kill process (Windows)
taskkill /PID <PID> /F

# Or use different port
# Edit docker-compose.dev.yml ports: "8503:8502"
```

### Container Won't Start

```bash
# Check logs
docker-compose -f docker-compose.dev.yml logs open_notebook

# Rebuild from scratch
docker-compose -f docker-compose.dev.yml down
docker-compose -f docker-compose.dev.yml build --no-cache open_notebook
docker-compose -f docker-compose.dev.yml up -d
```

### Python Import Errors

```bash
# Reinstall dependencies
docker exec open-notebook-open_notebook-1 uv sync
docker-compose -f docker-compose.dev.yml restart open_notebook
```

## WSL2 Development (Linux Hot Reload)

For full hot reload support on Windows:

```bash
# 1. Install WSL2 and Docker Desktop with WSL2 backend
# 2. Clone repo inside WSL2 (NOT /mnt/c/)
cd ~
git clone https://github.com/lfnovo/open-notebook.git
cd open-notebook

# 3. Develop in WSL2 filesystem
docker-compose -f docker-compose.dev.yml up -d

# Hot reload now works! File events propagate correctly.
```

**Why this works:** Files are in native Linux filesystem, so inotify events work properly.

## Performance Tips

### Faster Container Startup

```yaml
# In docker-compose.dev.yml, use cached volumes:
volumes:
  - ./notebook_data:/app/data:cached
  - .:/app:cached
```

### Reduce Polling Load

If performance is slow, increase polling interval:

```bash
# In supervisord.conf
CHOKIDAR_INTERVAL="1000"  # Poll every 1s instead of 100ms
```

### Native Frontend for Speed

Next.js builds are faster natively:

```bash
cd frontend
npm run dev  # Much faster than Docker on Windows/macOS
```

## Editor Setup

### VS Code

**Recommended Extensions:**
- Python (Microsoft)
- Pylance
- ESLint
- Prettier
- Tailwind CSS IntelliSense
- Docker

**Settings (`.vscode/settings.json`):**
```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/.venv/bin/python",
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.fixAll.eslint": true
  }
}
```

## Testing

### Run Tests

```bash
# Python tests
docker exec open-notebook-open_notebook-1 uv run pytest

# Frontend tests  
cd frontend
npm run test
```

### Code Quality

```bash
# Python linting
docker exec open-notebook-open_notebook-1 uv run ruff check .

# Frontend linting
cd frontend
npm run lint
```

## Next Steps

- See [CONFIGURATION.md](CONFIGURATION.md) for environment variables
- See [MIGRATION.md](MIGRATION.md) for database migrations
- See [CONTRIBUTING.md](CONTRIBUTING.md) for code style and PRs
- See [ORANGEPI_DEPLOYMENT.md](ORANGEPI_DEPLOYMENT.md) for production deployment
