# Single Container Deployment

For users who prefer an all-in-one container solution (e.g., PikaPods, Railway, simple cloud deployments), Open Notebook provides a single-container image that includes all services: SurrealDB, API backend, background worker, and React frontend.

## 📋 Overview

The single-container deployment packages everything you need:
- **SurrealDB**: Database service
- **FastAPI**: REST API backend  
- **Background Worker**: For podcast generation and transformations
- **Next.js**: Web UI interface

All services are managed by supervisord with proper startup ordering, making it perfect for platforms that prefer single-container deployments.

## 🚀 Quick Start

### Option 1: Docker Compose (Recommended)

This is the easiest way to get started with persistent data.

1. **Create a project directory**:
   ```bash
   mkdir open-notebook
   cd open-notebook
   ```

2. **Create a `docker-compose.single.yml` file**:
   ```yaml
   services:
     open_notebook_single:
       image: lfnovo/open_notebook:v1-latest-single
       ports:
         - "8502:8502"  # React frontend
         - "5055:5055"  # REST API
       environment:
         # Required: Add your API keys here
         - OPENAI_API_KEY=your_openai_key
         - ANTHROPIC_API_KEY=your_anthropic_key
         
         # Optional: Additional providers
         - GOOGLE_API_KEY=your_google_key
         - GROQ_API_KEY=your_groq_key
         
         # Optional: Password protection for public deployments
         - OPEN_NOTEBOOK_PASSWORD=your_secure_password
       volumes:
         - ./notebook_data:/app/data          # Application data
         - ./surreal_single_data:/mydata      # SurrealDB data
       restart: always
   ```

3. **Start the container**:
   ```bash
   docker compose -f docker-compose.single.yml up -d
   ```

4. **Access the application**:
   - React frontend: http://localhost:8502
   - REST API: http://localhost:5055
   - API Documentation: http://localhost:5055/docs

### Option 2: Direct Docker Run

For quick testing without docker-compose:

```bash
docker run -d \
  --name open-notebook-single \
  -p 8502:8502 \
  -p 5055:5055 \
  -v ./notebook_data:/app/data \
  -v ./surreal_single_data:/mydata \
  -e OPENAI_API_KEY=your_openai_key \
  -e ANTHROPIC_API_KEY=your_anthropic_key \
  -e OPEN_NOTEBOOK_PASSWORD=your_secure_password \
  lfnovo/open_notebook:v1-latest-single
```

## 🌐 Platform-Specific Deployments

### PikaPods

Perfect for PikaPods one-click deployment:

1. **Use this configuration**:
   ```
   Image: lfnovo/open_notebook:v1-latest-single
   Port: 8502
   ```

2. **Set environment variables in PikaPods**:
   ```
   OPENAI_API_KEY=your_openai_key
   OPEN_NOTEBOOK_PASSWORD=your_secure_password
   ```

3. **Mount volumes**:
   - `/app/data` for application data
   - `/mydata` for database files

### Railway

For Railway deployment:

1. **Connect your GitHub repository** or use the template
2. **Set environment variables**:
   ```
   OPENAI_API_KEY=your_openai_key
   OPEN_NOTEBOOK_PASSWORD=your_secure_password
   ```
3. **Configure volumes** in Railway dashboard for data persistence

### DigitalOcean App Platform

1. **Create a new app** from Docker Hub
2. **Use image**: `lfnovo/open_notebook:v1-latest-single`
3. **Set environment variables** in the app settings
4. **Configure persistent storage** for `/app/data` and `/mydata`

## 🔧 Configuration

### Environment Variables

The single-container deployment uses the same environment variables as the multi-container setup, but with SurrealDB configured for localhost connection:

```bash
# Database connection (automatically configured)
SURREAL_URL="ws://localhost:8000/rpc"
SURREAL_USER="root"
SURREAL_PASSWORD="root"
SURREAL_NAMESPACE="open_notebook"
SURREAL_DATABASE="staging"

# Required: At least one AI provider
OPENAI_API_KEY=your_openai_key

# Optional: Additional AI providers
ANTHROPIC_API_KEY=your_anthropic_key
GOOGLE_API_KEY=your_google_key
GROQ_API_KEY=your_groq_key
OLLAMA_API_BASE=http://your-ollama-host:11434

# Optional: Security for public deployments
OPEN_NOTEBOOK_PASSWORD=your_secure_password

# Optional: Advanced TTS
ELEVENLABS_API_KEY=your_elevenlabs_key
```

### Data Persistence

**Critical**: Always mount these volumes to persist data between container restarts:

1. **`/app/data`** - Application data (notebooks, sources, uploads)
2. **`/mydata`** - SurrealDB database files

**Example with proper volumes**:
```yaml
volumes:
  - ./notebook_data:/app/data          # Your notebooks and sources
  - ./surreal_single_data:/mydata      # Database files
```

## 🔒 Security

### Password Protection

For public deployments, **always set a password**:

```bash
OPEN_NOTEBOOK_PASSWORD=your_secure_password
```

This protects both the React frontend and REST API with password authentication.

### Security Best Practices

1. **Use HTTPS**: Deploy behind a reverse proxy with SSL
2. **Strong Password**: Use a complex, unique password
3. **Regular Updates**: Keep the container image updated
4. **Network Security**: Configure firewall rules appropriately
5. **Monitor Access**: Check logs for suspicious activity

## 🏗️ Building from Source

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

## 📊 Service Management

### Startup Order

Services start in this order with proper delays:
1. **SurrealDB** (5 seconds startup time)
2. **API Backend** (3 seconds startup time)
3. **Background Worker** (3 seconds startup time)
4. **React frontend** (5 seconds startup time)

### Service Monitoring

All services are managed by supervisord. Check service status:

```bash
# View all services
docker exec -it open-notebook-single supervisorctl status

# View specific service logs
docker exec -it open-notebook-single supervisorctl tail -f api
docker exec -it open-notebook-single supervisorctl tail -f streamlit
```

## 💻 Resource Requirements

### Minimum Requirements
- **Memory**: 1GB RAM
- **CPU**: 1 core
- **Storage**: 10GB (for data persistence)
- **Network**: Internet connection for AI providers

### Recommended for Production
- **Memory**: 2GB+ RAM
- **CPU**: 2+ cores
- **Storage**: 50GB+ (for larger datasets)
- **Network**: Stable high-speed internet

## 🔍 Troubleshooting

### Container Won't Start

**Check the logs**:
```bash
docker logs open-notebook-single
```

**Common issues**:
- Insufficient memory (increase to 2GB+)
- Port conflicts (change port mapping)
- Missing API keys (check environment variables)

### Database Connection Issues

**Symptoms**: API errors, empty notebooks, connection timeouts

**Solutions**:
1. **Check memory**: SurrealDB needs at least 512MB
2. **Verify volumes**: Ensure `/mydata` is mounted and writable
3. **Check startup order**: Wait for full startup (30-60 seconds)
4. **Restart container**: Sometimes a fresh start helps

### Service Startup Problems

**Check individual services**:
```bash
# Enter the container
docker exec -it open-notebook-single bash

# Check service status
supervisorctl status

# Restart specific service
supervisorctl restart api
supervisorctl restart streamlit
```

### Performance Issues

**Symptoms**: Slow response times, timeouts

**Solutions**:
1. **Increase memory**: Allocate 2GB+ RAM
2. **Check CPU**: Ensure adequate CPU resources
3. **Monitor logs**: Look for performance bottlenecks
4. **Optimize models**: Use faster models for real-time tasks

## 📊 Comparison: Single vs Multi-Container

| Feature | Single-Container | Multi-Container |
|---------|------------------|-----------------|
| **Deployment** | One container | Multiple containers |
| **Complexity** | Simple | More complex |
| **Scaling** | All services together | Independent scaling |
| **Resource Control** | Shared resources | Fine-grained control |
| **Debugging** | All logs in one place | Separate service logs |
| **Platform Support** | Excellent for PaaS | Better for Kubernetes |
| **Memory Usage** | More efficient | More flexible |
| **Startup Time** | Faster | Slower |

## 🎯 When to Use Single-Container

### ✅ Use Single-Container When:
- **Platform requirements**: PikaPods, Railway, or similar platforms
- **Simple deployment**: You want the easiest possible setup
- **Resource constraints**: Limited memory/CPU resources
- **Quick testing**: Rapid deployment for testing
- **Single user**: Personal use without scaling needs

### ❌ Use Multi-Container When:
- **Production scaling**: Need to scale services independently
- **Resource optimization**: Want fine-grained resource control
- **Development**: Building/debugging the application
- **High availability**: Need service-level redundancy
- **Complex networking**: Custom networking requirements

## 🆘 Getting Help

### Quick Diagnostics

Before asking for help, gather this information:

```bash
# Container status
docker ps

# Container logs
docker logs open-notebook-single

# Service status inside container
docker exec -it open-notebook-single supervisorctl status

# Resource usage
docker stats open-notebook-single
```

### Community Support

- **[Discord Server](https://discord.gg/37XJPXfz2w)** - Real-time help and discussion
- **[GitHub Issues](https://github.com/lfnovo/open-notebook/issues)** - Bug reports and feature requests
- **[Documentation](../index.md)** - Complete documentation

### Common Solutions

1. **Port conflicts**: Change port mapping in docker-compose
2. **Memory issues**: Increase container memory allocation
3. **Volume permissions**: Ensure mounted volumes are writable
4. **API key errors**: Verify environment variables are set correctly
5. **Startup timeouts**: Wait 60+ seconds for full service startup

---

**Ready to deploy?** Start with Option 1 (Docker Compose) above for the best experience!