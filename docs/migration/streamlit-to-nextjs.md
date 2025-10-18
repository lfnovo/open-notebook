# Migration Guide: Next.js to Next.js Frontend

**Complete guide for upgrading from the React frontend to the new Next.js frontend.**

## Overview

Open Notebook has migrated from a Next.js-based user interface to a modern Next.js/React frontend. This upgrade provides:

- **Improved Performance**: Faster page loads and smoother interactions
- **Modern UI/UX**: Contemporary design with better responsiveness
- **Enhanced Features**: Better real-time updates and interactivity
- **Future-Ready**: Foundation for upcoming features like live updates

## What's Changing

### User Interface
- **Old**: Next.js-based UI (Python/Next.js)
- **New**: Next.js/React frontend (JavaScript/TypeScript)

### What Stays the Same
- ✅ **Same Port**: Still runs on port 8502
- ✅ **API Unchanged**: REST API remains on port 5055
- ✅ **Data Intact**: All your notebooks, sources, and notes are preserved
- ✅ **Configuration**: Same environment variables and settings
- ✅ **Features**: All existing functionality works the same way

## Upgrade Instructions

### For Docker Users (Recommended)

#### Single-Container Setup

1. **Stop the current container**:
   ```bash
   docker compose down
   ```

2. **Pull the latest image**:
   ```bash
   docker compose pull
   ```

3. **Start with the new version**:
   ```bash
   docker compose up -d
   ```

4. **Verify it's running**:
   - Open http://localhost:8502 in your browser
   - You should see the new Next.js interface

#### Multi-Container Setup

Same steps as above - the process is identical.

### For Development Setup

If you're running Open Notebook from source:

1. **Pull the latest changes**:
   ```bash
   git pull origin main
   ```

2. **Install frontend dependencies**:
   ```bash
   cd frontend
   npm install
   npm run build
   cd ..
   ```

3. **Start the application**:
   ```bash
   make start-all
   ```

4. **Access the new interface**:
   - Frontend: http://localhost:8502
   - API: http://localhost:5055

## Verification Steps

After upgrading, verify everything works correctly:

1. **Check the UI loads**:
   - Navigate to http://localhost:8502
   - You should see a modern interface with a cleaner design

2. **Test your notebooks**:
   - Open an existing notebook
   - Verify sources are visible
   - Check notes are accessible
   - Try the chat functionality

3. **Test core features**:
   - Create a new notebook
   - Add a source (URL, file, or text)
   - Generate a note
   - Search your content
   - Start a chat session

4. **Check API access** (if you use it):
   - Navigate to http://localhost:5055/docs
   - API documentation should be accessible
   - Test any custom integrations

## Troubleshooting

### UI Doesn't Load

**Symptom**: Browser shows error or blank page at http://localhost:8502

**Solutions**:
1. Check container logs:
   ```bash
   docker compose logs -f open_notebook
   ```

2. Verify container is running:
   ```bash
   docker compose ps
   ```

3. Try restarting:
   ```bash
   docker compose restart open_notebook
   ```

### Port Conflicts

**Symptom**: Error about port 8502 already in use

**Solutions**:
1. Check what's using the port:
   ```bash
   # macOS/Linux
   lsof -i :8502

   # Windows
   netstat -ano | findstr :8502
   ```

2. Stop the conflicting service or change Open Notebook's port:
   ```yaml
   # In docker-compose.yml
   ports:
     - "8503:8502"  # Maps host port 8503 to container port 8502
   ```

### Data Not Showing

**Symptom**: Notebooks or sources appear empty

**Solutions**:
1. Verify volume mounts are correct:
   ```bash
   docker compose config
   ```

2. Check database is running (multi-container):
   ```bash
   docker compose ps surrealdb
   ```

3. Verify data directories exist:
   ```bash
   ls -la notebook_data/
   ls -la surreal_data/
   ```

### API Errors

**Symptom**: Frontend shows "Cannot connect to API" or similar errors

**Solutions**:
1. Verify API is running:
   ```bash
   curl http://localhost:5055/health
   ```

2. Check API logs:
   ```bash
   docker compose logs -f open_notebook | grep api
   ```

3. Ensure environment variables are set:
   ```bash
   docker compose exec open_notebook env | grep SURREAL
   ```

## Rollback Instructions

If you need to rollback to the Next.js version:

### Quick Rollback

1. **Stop current containers**:
   ```bash
   docker compose down
   ```

2. **Use a specific older version** (replace with your previous version):
   ```bash
   # In docker-compose.yml, change:
   image: lfnovo/open_notebook:0.1.45-single  # or whatever version you had
   ```

3. **Start the old version**:
   ```bash
   docker compose up -d
   ```

### Finding Your Previous Version

Check your Docker images:
```bash
docker images | grep open_notebook
```

Or check the [releases page](https://github.com/lfnovo/open-notebook/releases) for version numbers.

## Frequently Asked Questions

### Do I need to backup before upgrading?

While the upgrade process doesn't modify your data, it's always a good practice to backup:

```bash
# Backup your data
tar -czf backup-$(date +%Y%m%d).tar.gz notebook_data surreal_data
```

### Will my bookmarks still work?

Yes! The new frontend still runs on port 8502, so all your bookmarks will continue to work.

### Do I need to reconfigure AI models?

No, all your model configurations are stored in the database and will work automatically with the new UI.

### Will my API integrations break?

No, the API is completely unchanged. All existing integrations will continue to work.

### What if I prefer the old React frontend?

You can rollback to any previous version using the instructions above. However, we recommend trying the new UI as it provides better performance and will receive all future updates.

### How do I report issues with the new UI?

Please report any issues on our [GitHub Issues page](https://github.com/lfnovo/open-notebook/issues) or join our [Discord server](https://discord.gg/37XJPXfz2w) for help.

## New Features in Next.js UI

While the migration maintains feature parity, the new frontend enables:

- **Better Performance**: Faster loading and navigation
- **Improved Responsiveness**: Better mobile and tablet support
- **Modern Design**: Cleaner, more intuitive interface
- **Foundation for Future**: Enables upcoming features like real-time collaboration

## Getting Help

If you encounter any issues during migration:

1. **Check the logs**: `docker compose logs -f`
2. **Review this guide**: Most issues are covered in Troubleshooting
3. **Join Discord**: [discord.gg/37XJPXfz2w](https://discord.gg/37XJPXfz2w)
4. **Open an issue**: [GitHub Issues](https://github.com/lfnovo/open-notebook/issues)

## Post-Migration Checklist

After successfully migrating, complete these steps:

- [ ] Verify all notebooks load correctly
- [ ] Test source addition and viewing
- [ ] Verify notes are accessible
- [ ] Test chat functionality
- [ ] Check search works as expected
- [ ] Verify podcast generation (if used)
- [ ] Test any custom API integrations
- [ ] Update any deployment documentation you maintain
- [ ] Remove old Docker images to free space: `docker image prune`

---

**Questions?** Join our [Discord community](https://discord.gg/37XJPXfz2w) or [open an issue](https://github.com/lfnovo/open-notebook/issues) on GitHub.
