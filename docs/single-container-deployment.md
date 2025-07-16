# Single-Container Deployment Guide

For users who prefer an all-in-one container solution (e.g., PikaPods, simple deployments), Open Notebook provides a single-container image that includes all services: SurrealDB, API backend, background worker, and Streamlit UI.

## Overview

The single-container deployment packages:
- **SurrealDB**: Database service
- **FastAPI**: REST API backend  
- **Background Worker**: For podcast generation and transformations
- **Streamlit**: Web UI interface

All services are managed by supervisord with proper startup ordering.

## Quick Start

### Option 1: Using Docker Compose (Recommended)

1. Create a `docker-compose.single.yml` file:

```yaml
services:
  open_notebook_single:
    image: lfnovo/open_notebook:latest-single
    ports:
      - "8502:8502"  # Streamlit UI
      - "5055:5055"  # REST API
    environment:
      # Add your API keys here
      - OPENAI_API_KEY=your_openai_key
      - ANTHROPIC_API_KEY=your_anthropic_key
      # ... other environment variables
    volumes:
      - ./notebook_data:/app/data          # Application data
      - ./surreal_single_data:/mydata      # SurrealDB data
    restart: always
```

2. Run the container:

```bash
docker compose -f docker-compose.single.yml up -d
```

### Option 2: Direct Docker Run

```bash
docker run -d \
  --name open-notebook-single \
  -p 8502:8502 \
  -p 5055:5055 \
  -v ./notebook_data:/app/data \
  -v ./surreal_single_data:/mydata \
  -e OPENAI_API_KEY=your_openai_key \
  -e ANTHROPIC_API_KEY=your_anthropic_key \
  lfnovo/open_notebook:latest-single
```

### Option 3: PikaPods Deployment

For PikaPods users, use the single-container image:

```
Image: lfnovo/open_notebook:latest-single
Port: 8502
```

Add your API keys as environment variables in the PikaPods configuration.

## Environment Variables

The single-container deployment uses the same environment variables as the multi-container setup, but with SurrealDB configured for localhost connection:

```bash
# Database connection (automatically configured)
SURREAL_URL="ws://localhost:8000/rpc"
SURREAL_USER="root"
SURREAL_PASSWORD="root"
SURREAL_NAMESPACE="open_notebook"
SURREAL_DATABASE="staging"

# API Keys (configure these)
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key
GEMINI_API_KEY=your_gemini_key
# ... other provider keys
```

## Service Access

Once running, access the services at:

- **Streamlit UI**: http://localhost:8502
- **REST API**: http://localhost:5055
- **API Documentation**: http://localhost:5055/docs

## Data Persistence

The single-container setup uses two volume mounts:

1. `/app/data` - Application data (notebooks, sources, etc.)
2. `/mydata` - SurrealDB database files

Make sure to mount these volumes to persist data between container restarts.

## Security

For public deployments, always set the `OPEN_NOTEBOOK_PASSWORD` environment variable:

```bash
OPEN_NOTEBOOK_PASSWORD=your_secure_password
```

This protects both the Streamlit UI and REST API with password authentication.

## Building from Source

To build the single-container image yourself:

```bash
# Clone the repository
git clone https://github.com/lfnovo/open-notebook
cd open-notebook

# Build the single-container image
make docker-build-single-dev

# Or build with multi-platform support
make docker-build-single
```

## Troubleshooting

### Container Won't Start

Check the logs to see which service is failing:

```bash
docker logs open-notebook-single
```

### Database Connection Issues

The single-container uses localhost for SurrealDB. If you see connection errors, ensure:

1. The container has enough memory (minimum 1GB recommended)
2. No port conflicts on 8000 (SurrealDB internal port)
3. The `/mydata` volume is properly mounted and writable

### Service Startup Order

Services start in this order:
1. SurrealDB (5 seconds startup time)
2. API Backend (3 seconds startup time)
3. Background Worker (3 seconds startup time)
4. Streamlit UI (5 seconds startup time)

If services fail to start, check the supervisord logs in the container.

## Resource Requirements

**Minimum Requirements:**
- Memory: 1GB RAM
- CPU: 1 core
- Storage: 10GB (for data persistence)

**Recommended:**
- Memory: 2GB+ RAM
- CPU: 2+ cores
- Storage: 50GB+ (for larger datasets)

## Differences from Multi-Container

| Feature | Multi-Container | Single-Container |
|---------|-----------------|------------------|
| Database | Separate SurrealDB container | Built-in SurrealDB |
| Scaling | Can scale services independently | All services in one container |
| Resource Usage | More flexible resource allocation | Fixed resource sharing |
| Deployment | Requires docker-compose | Single container run |
| Complexity | More complex setup | Simpler deployment |
| Debugging | Easier to debug individual services | All logs in one container |

## When to Use Single-Container

**Use single-container when:**
- Deploying to platforms like PikaPods
- You want the simplest possible deployment
- Resource constraints favor single container
- You don't need to scale services independently

**Use multi-container when:**
- You need fine-grained resource control
- You want to scale services independently
- You prefer traditional microservices architecture
- You need to debug individual services easily