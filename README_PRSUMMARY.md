# PMOVES Integration – Open Notebook Docker + GHCR

Adds GHCR publish workflow and pmoves-net compose. Runs UI on :8503 and API on :5056.

Usage:
```bash
docker network create pmoves-net || true
docker compose -f docker-compose.pmoves-net.yml up -d
# UI: http://localhost:8503, API: http://localhost:5056
```

Image: `ghcr.io/POWERFULMOVES/Pmoves-open-notebook:main`.
