# Single Container Installation

All-in-one container setup. **Simpler than Docker Compose, but less flexible.**

**Best for:** PikaPods, Railway, shared hosting, minimal setups

> **Alternative Registry:** Images available on both Docker Hub (`lfnovo/open_notebook:v1-latest-single`) and GitHub Container Registry (`ghcr.io/lfnovo/open-notebook:v1-latest-single`).

> **Note**: While this is a simple way to get started, we recommend [Docker Compose](docker-compose.md) for most users. Docker Compose is more flexible and will make it easier if we add more services to the setup in the future. This single-container option is best for platforms that specifically require it (PikaPods, Railway, etc.).

## Prerequisites

- Docker installed (for local testing)
- API key from OpenAI, Anthropic, or another provider
- 5 minutes

## Quick Setup

### For Local Testing (Docker)

```yaml
# docker-compose.yml
services:
  open_notebook:
    image: lfnovo/open_notebook:v1-latest-single
    pull_policy: always
    ports:
      - "8502:8502"  # Web UI (React frontend)
      - "5055:5055"  # API
    environment:
      - OPEN_NOTEBOOK_ENCRYPTION_KEY=change-me-to-a-secret-string
      - SURREAL_URL=ws://localhost:8000/rpc
      - SURREAL_USER=root
      - SURREAL_PASSWORD=password
      - SURREAL_NAMESPACE=open_notebook
      - SURREAL_DATABASE=open_notebook
    volumes:
      - ./data:/app/data
    restart: always
```

Run:
```bash
docker compose up -d
```

Access: `http://localhost:8502`

Then configure your AI provider:
1. Go to **Settings** → **API Keys**
2. Click **Add Credential** → Select your provider → Paste API key
3. Click **Save**, then **Test Connection**
4. Click **Discover Models** → **Register Models**

### For Cloud Platforms

**PikaPods:**
1. Click "New App"
2. Search "Open Notebook"
3. Set environment variables (at minimum: `OPEN_NOTEBOOK_ENCRYPTION_KEY`)
4. Click "Deploy"
5. Open the app → Go to **Settings → API Keys** to configure your AI provider

**Railway:**
1. Create new project
2. Add `lfnovo/open_notebook:v1-latest-single`
3. Set environment variables (at minimum: `OPEN_NOTEBOOK_ENCRYPTION_KEY`)
4. Deploy
5. Open the app → Go to **Settings → API Keys** to configure your AI provider

**Render:**
1. Create new Web Service
2. Use Docker image: `lfnovo/open_notebook:v1-latest-single`
3. Set environment variables in dashboard (at minimum: `OPEN_NOTEBOOK_ENCRYPTION_KEY`)
4. Configure persistent disk for `/app/data` and `/mydata`

**DigitalOcean App Platform:**
1. Create new app from Docker Hub
2. Use image: `lfnovo/open_notebook:v1-latest-single`
3. Set port to 8502
4. Add environment variables (at minimum: `OPEN_NOTEBOOK_ENCRYPTION_KEY`)
5. Configure persistent storage

**Heroku:**
```bash
# Using heroku.yml
heroku container:push web
heroku container:release web
heroku config:set OPEN_NOTEBOOK_ENCRYPTION_KEY=your-secret-key
```

**Coolify:**
1. Add new service → Docker Image
2. Image: `lfnovo/open_notebook:v1-latest-single`
3. Port: 8502
4. Add environment variables (at minimum: `OPEN_NOTEBOOK_ENCRYPTION_KEY`)
5. Enable persistent volumes
6. Coolify handles HTTPS automatically

---

## Environment Variables

| Variable | Purpose | Example |
|----------|---------|---------|
| `OPEN_NOTEBOOK_ENCRYPTION_KEY` | Encryption key for credentials (required) | `my-secret-key` |
| `SURREAL_URL` | Database | `ws://localhost:8000/rpc` |
| `SURREAL_USER` | DB user | `root` |
| `SURREAL_PASSWORD` | DB password | `password` |
| `API_URL` | External URL (for remote access) | `https://myapp.example.com` |

AI provider API keys are configured via the **Settings → API Keys** UI after deployment.

---

## Limitations vs Docker Compose

| Feature | Single Container | Docker Compose |
|---------|------------------|-----------------|
| Setup time | 2 minutes | 5 minutes |
| Complexity | Minimal | Moderate |
| Services | All bundled | Separated |
| Scalability | Limited | Excellent |
| Memory usage | ~800MB | ~1.2GB |

---

## Next Steps

Same as Docker Compose setup - just access via `http://localhost:8502` (local) or your platform's URL (cloud).

1. Go to **Settings → API Keys** to add your AI provider credential
2. **Test Connection** and **Discover Models**

See [Docker Compose](docker-compose.md) for full post-install guide.
