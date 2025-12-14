# Development Watch Mode Guide

## Overview

The development environment is now configured with **hot reload** for both frontend and backend:

### ✅ What's Enabled

1. **Frontend (Next.js)**: Auto-reloads on file changes
   - Edit any `.tsx`, `.ts`, `.css` file in `frontend/src/`
   - Changes appear in browser automatically (Fast Refresh)
   - No rebuild needed

2. **Backend (FastAPI)**: Auto-reloads on file changes
   - Edit any `.py` file in `api/` or `open_notebook/`
   - API server restarts automatically
   - Typically takes 2-3 seconds to reload

3. **Source Code Mounted**: All code is mounted from your local filesystem
   - Changes are immediately visible to the container
   - No need to rebuild for code changes

### 🚀 Quick Start

```powershell
# Start development environment
docker-compose -f docker-compose.dev.yml up

# Or rebuild if dependencies changed
docker-compose -f docker-compose.dev.yml up --build
```

### 📝 When to Rebuild

You **only** need to rebuild (`--build`) if you:
- Change `package.json` (add/remove npm packages)
- Change `pyproject.toml` (add/remove Python packages)
- Change `Dockerfile.dev`
- Change system dependencies

For **code changes only**, just save the file - it will hot reload!

### 🔍 Watching the Logs

```powershell
# Watch all services
docker-compose -f docker-compose.dev.yml logs -f

# Watch only frontend
docker-compose -f docker-compose.dev.yml logs -f open_notebook | Select-String "frontend"

# Watch only API
docker-compose -f docker-compose.dev.yml logs -f open_notebook | Select-String "api"
```

### ⚡ Development Workflow

1. **Edit Code**: Make changes to any file in `frontend/src/`, `api/`, or `open_notebook/`
2. **Save**: Ctrl+S in your editor
3. **Wait**: 1-3 seconds for reload
4. **Test**: Refresh browser (or automatic with Fast Refresh)

### 🛠️ Troubleshooting

**Frontend not reloading?**
- Check logs: `docker-compose -f docker-compose.dev.yml logs -f open_notebook`
- Ensure you're accessing `http://localhost:8502`
- Try hard refresh: Ctrl+Shift+R

**Backend not reloading?**
- Check for syntax errors in Python files
- Look for error messages in logs
- Uvicorn will show reload messages when it detects changes

**Changes not appearing?**
- Ensure the file is saved
- Check that the file is inside a mounted directory
- Verify the container is running: `docker-compose -f docker-compose.dev.yml ps`

### 📦 What's NOT Hot Reloadable

These require a rebuild:
- Installing new npm packages
- Installing new Python packages
- Changing environment variables in `docker.env`
- Modifying `Dockerfile.dev`

### 🎯 Performance Tips

- **Windows Users**: If reloading is slow, ensure WSL2 is being used for Docker
- **File System**: Code in WSL2 filesystem reloads faster than Windows NTFS
- **Exclude Large Directories**: node_modules and .venv are excluded for performance

### 📊 Service Ports

- **Frontend**: http://localhost:8502
- **API**: http://localhost:5055/docs (Swagger UI)
- **Ollama**: http://localhost:11434
- **Whisper**: http://localhost:9000

### 🔄 Quick Commands

```powershell
# Stop services
docker-compose -f docker-compose.dev.yml down

# Restart a specific service
docker-compose -f docker-compose.dev.yml restart open_notebook

# Rebuild and restart
docker-compose -f docker-compose.dev.yml up --build -d

# View running containers
docker-compose -f docker-compose.dev.yml ps
```

## Happy Coding! 🎉
