# Migration Guide: Streamlit to React/Next.js Frontend

**Version**: 1.0.0
**Last Updated**: October 2025

This guide helps existing Open Notebook users migrate from the legacy Streamlit frontend to the new React/Next.js frontend.

## What Changed

Open Notebook has migrated from a Streamlit-based frontend to a modern React/Next.js application. This brings significant improvements in performance, user experience, and maintainability.

### Key Changes

| Aspect | Before (Streamlit) | After (React/Next.js) |
|--------|-------------------|----------------------|
| **Frontend Framework** | Streamlit | Next.js 15 + React 18 |
| **UI Components** | Streamlit widgets | shadcn/ui + Radix UI |
| **Frontend Port** | 8502 | 8502 (unchanged) |
| **API Port** | 5055 | 5055 (unchanged) |
| **Navigation** | Sidebar with emoji icons | Clean sidebar navigation |
| **Performance** | Server-side rendering | Client-side React with API calls |
| **Customization** | Limited | Highly customizable |

### What Stayed the Same

- **Core functionality**: All features remain available
- **API backend**: FastAPI backend unchanged
- **Database**: SurrealDB unchanged
- **Data format**: No data migration needed
- **Configuration**: Same environment variables
- **Docker deployment**: Same ports and setup

## Migration Paths

### Path 1: Docker Users (Recommended)

If you're running Open Notebook via Docker, migration is automatic:

1. **Stop the current version**:
   ```bash
   docker-compose down
   ```

2. **Update to the latest image**:
   ```bash
   # Update docker-compose.yml to use v1-latest
   # Change from:
   image: lfnovo/open_notebook:latest-single
   # To:
   image: lfnovo/open_notebook:v1-latest-single
   ```

3. **Start the new version**:
   ```bash
   docker-compose pull
   docker-compose up -d
   ```

4. **Access the new frontend**:
   - Frontend: http://localhost:8502 (new React UI)
   - API Docs: http://localhost:5055/docs

**Your data is automatically preserved!** All notebooks, sources, and notes carry over seamlessly.

### Path 2: Source Code Users

If you're running from source code:

1. **Pull the latest code**:
   ```bash
   git pull origin main
   ```

2. **Install frontend dependencies**:
   ```bash
   cd frontend
   npm install
   cd ..
   ```

3. **Update Python dependencies**:
   ```bash
   uv sync
   ```

4. **Start services** (3 terminals):
   ```bash
   # Terminal 1: Database
   make database

   # Terminal 2: API
   uv run python api/main.py

   # Terminal 3: Frontend (NEW)
   cd frontend && npm run dev
   ```

5. **Access the application**:
   - Frontend: http://localhost:8502
   - API: http://localhost:5055

## Breaking Changes

### Removed Features

The following Streamlit-specific features are no longer available:

- **Streamlit cache**: Replaced with React Query caching
- **Streamlit session state**: Replaced with React state management
- **Direct file access via Streamlit**: Use API endpoints instead

### Changed Navigation

Navigation paths have been simplified:

| Old Path | New Path |
|----------|----------|
| Settings → Models | Models |
| Settings → Advanced | Advanced |
| Other paths | (Same but cleaner navigation) |

### API Changes

**No breaking API changes!** The REST API remains fully backward compatible.

## New Features in React Version

The React frontend brings several improvements:

### Performance
- **Faster page loads**: Client-side rendering with React
- **Better caching**: React Query for intelligent data caching
- **Optimized builds**: Next.js automatic code splitting

### User Experience
- **Modern UI**: Clean, professional interface with shadcn/ui
- **Responsive design**: Better mobile and tablet support
- **Keyboard shortcuts**: Improved keyboard navigation
- **Real-time updates**: Better WebSocket support

### Developer Experience
- **TypeScript**: Full type safety
- **Component library**: Reusable UI components
- **Hot reload**: Instant updates during development
- **Testing**: Better test infrastructure

## Troubleshooting

### Issue: Can't access the frontend

**Solution**:
```bash
# Check if services are running
docker-compose ps

# Check logs
docker-compose logs open_notebook

# Restart services
docker-compose restart
```

### Issue: API errors in new frontend

**Solution**:
The new frontend requires the API to be running. Ensure:
```bash
# API should be accessible at
curl http://localhost:5055/health

# If not, check API logs
docker-compose logs open_notebook | grep api
```

### Issue: Missing data after migration

**Solution**:
Data is preserved automatically. If you don't see your data:

1. Check database volume is mounted correctly:
   ```bash
   docker-compose down
   # Verify volumes in docker-compose.yml:
   # - ./surreal_data:/mydata  (for multi-container)
   # - ./surreal_single_data:/mydata (for single-container)
   docker-compose up -d
   ```

2. Check SurrealDB is running:
   ```bash
   docker-compose logs surrealdb
   ```

### Issue: Port conflicts

**Solution**:
If ports 8502 or 5055 are already in use:

```bash
# Find what's using the port
lsof -i :8502
lsof -i :5055

# Stop conflicting service or change Open Notebook ports
# Edit docker-compose.yml:
ports:
  - "8503:8502"  # Change external port
  - "5056:5055"  # Change external port
```

## Rollback Instructions

If you need to roll back to the Streamlit version:

### Docker Users

```bash
# Stop current version
docker-compose down

# Edit docker-compose.yml to use old image
# Change to: lfnovo/open_notebook:streamlit-latest

# Start old version
docker-compose up -d
```

### Source Code Users

```bash
# Checkout the last Streamlit version tag
git checkout tags/streamlit-final

# Install dependencies
uv sync

# Start Streamlit
uv run streamlit run app_home.py
```

## Getting Help

If you encounter issues during migration:

- **Discord**: Join our [Discord community](https://discord.gg/37XJPXfz2w) for real-time help
- **GitHub Issues**: Report bugs at [github.com/lfnovo/open-notebook/issues](https://github.com/lfnovo/open-notebook/issues)
- **Documentation**: Check [full documentation](https://github.com/lfnovo/open-notebook/tree/main/docs)

## FAQs

### Will my notebooks and data be lost?
No! All data is preserved. The database and API backend are unchanged.

### Do I need to update my API integrations?
No! The REST API remains fully backward compatible.

### Can I use both frontends simultaneously?
Technically yes, but not recommended. Choose one for consistency.

### What about my custom Streamlit pages?
Custom Streamlit pages won't work with the React frontend. Consider:
- Using the REST API to build custom integrations
- Contributing React components to the project
- Requesting features in GitHub issues

### Is the Streamlit version still supported?
The Streamlit version is no longer actively developed. We recommend migrating to the React version for the best experience and latest features.

## Timeline

- **Legacy (Pre-v1.0)**: Streamlit frontend
- **Current (v1.0+)**: React/Next.js frontend
- **Future**: Continued React development with new features

---

**Ready to migrate?** Follow the migration path for your deployment method above. The process is straightforward and your data is safe!
