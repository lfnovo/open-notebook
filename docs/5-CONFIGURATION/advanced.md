# Advanced Configuration

Performance tuning, debugging, and advanced features.

---

## Performance Tuning

### Concurrency Control

```env
# Max concurrent database operations (default: 5)
# Increase: Faster processing, more conflicts
# Decrease: Slower, fewer conflicts
SURREAL_COMMANDS_MAX_TASKS=5
```

**Guidelines:**
- CPU: 2 cores → 2-3 tasks
- CPU: 4 cores → 5 tasks (default)
- CPU: 8+ cores → 10-20 tasks

Higher concurrency = more throughput but more database conflicts (retries handle this).

### Retry Strategy

```env
# How to wait between retries
SURREAL_COMMANDS_RETRY_WAIT_STRATEGY=exponential_jitter

# Options:
# - exponential_jitter (recommended)
# - exponential
# - fixed
# - random
```

For high-concurrency deployments, use `exponential_jitter` to prevent thundering herd.

### Timeout Tuning

```env
# Client timeout (default: 300 seconds)
API_CLIENT_TIMEOUT=300

# LLM timeout (default: 60 seconds)
ESPERANTO_LLM_TIMEOUT=60
```

**Guideline:** Set `API_CLIENT_TIMEOUT` > `ESPERANTO_LLM_TIMEOUT` + buffer

```
Example:
  ESPERANTO_LLM_TIMEOUT=120
  API_CLIENT_TIMEOUT=180  # 120 + 60 second buffer
```

---

## Batching

### TTS Batch Size

For podcast generation, control concurrent TTS requests:

```env
# Default: 5
TTS_BATCH_SIZE=2
```

**Providers and recommendations:**
- OpenAI: 5 (can handle many concurrent)
- Google: 4 (good concurrency)
- ElevenLabs: 2 (limited concurrent requests)
- Local TTS: 1 (single-threaded)

Lower = slower but more stable. Higher = faster but more load on provider.

---

## Logging & Debugging

### Enable Detailed Logging

```bash
# Start with debug logging
RUST_LOG=debug  # For Rust components
LOGLEVEL=DEBUG  # For Python components
```

### Debug Specific Components

```bash
# Only surreal operations
RUST_LOG=surrealdb=debug

# Only langchain
LOGLEVEL=langchain:debug

# Only specific module
RUST_LOG=open_notebook::database=debug
```

### LangSmith Tracing

For debugging LLM workflows:

```env
LANGCHAIN_TRACING_V2=true
LANGCHAIN_ENDPOINT="https://api.smith.langchain.com"
LANGCHAIN_API_KEY=your-key
LANGCHAIN_PROJECT="Open Notebook"
```

Then visit https://smith.langchain.com to see traces.

---

## Port Configuration

### Default Ports

```
Frontend: 8502 (Docker deployment)
Frontend: 3000 (Development from source)
API: 5055
SurrealDB: 8000
```

### Changing Frontend Port

Edit `docker-compose.yml`:

```yaml
services:
  open-notebook:
    ports:
      - "8001:8502"  # Change from 8502 to 8001
```

Access at: `http://localhost:8001`

API auto-detects to: `http://localhost:5055` ✓

### Changing API Port

```yaml
services:
  open-notebook:
    ports:
      - "127.0.0.1:8502:8502"  # Frontend
      - "5056:5055"            # Change API from 5055 to 5056
    environment:
      - API_URL=http://localhost:5056  # Update API_URL
```

Access API directly: `http://localhost:5056/docs`

**Note:** When changing API port, you must set `API_URL` explicitly since auto-detection assumes port 5055.

### Changing SurrealDB Port

```yaml
services:
  surrealdb:
    ports:
      - "8001:8000"  # Change from 8000 to 8001
    environment:
      - SURREAL_URL=ws://surrealdb:8001/rpc  # Update connection URL
```

**Important:** Internal Docker network uses container name (`surrealdb`), not `localhost`.

---

## SSL/TLS Configuration

### Custom CA Certificate

For self-signed certs on local providers:

```env
ESPERANTO_SSL_CA_BUNDLE=/path/to/ca-bundle.pem
```

### Disable Verification (Development Only)

```env
# WARNING: Only for testing/development
# Vulnerable to MITM attacks
ESPERANTO_SSL_VERIFY=false
```

---

## Multi-Provider Setup

### Use Different Providers for Different Tasks

```env
# Language model (main)
OPENAI_API_KEY=sk-proj-...

# Embeddings (alternative)
# (Future: Configure different embedding provider)

# TTS (different provider)
ELEVENLABS_API_KEY=...
```

### OpenAI-Compatible with Fallback

```env
# Primary
OPENAI_COMPATIBLE_BASE_URL=http://localhost:1234/v1
OPENAI_COMPATIBLE_API_KEY=key1

# Can also set specific modality endpoints
OPENAI_COMPATIBLE_BASE_URL_LLM=http://localhost:1234/v1
OPENAI_COMPATIBLE_BASE_URL_EMBEDDING=http://localhost:8001/v1
```

---

## Security Hardening

### Change Default Credentials

```env
# Don't use defaults in production
SURREAL_USER=your_secure_username
SURREAL_PASSWORD=$(openssl rand -base64 32)  # Generate secure password
```

### Add Password Protection

```env
# Protect your Open Notebook instance
OPEN_NOTEBOOK_PASSWORD=your_secure_password
```

### Use HTTPS

```env
# Always use HTTPS in production
API_URL=https://mynotebook.example.com
```

### Firewall Rules

Restrict access to your Open Notebook:
- Port 8502 (frontend): Only from your IP
- Port 5055 (API): Only from frontend
- Port 8000 (SurrealDB): Never expose to internet

---

## Web Scraping & Content Extraction

Open Notebook uses multiple services for content extraction:

### Firecrawl

For advanced web scraping:

```env
FIRECRAWL_API_KEY=your-key
```

Get key from: https://firecrawl.dev/

### Jina AI

Alternative web extraction:

```env
JINA_API_KEY=your-key
```

Get key from: https://jina.ai/

---

## Environment Variable Groups

### API Keys (Choose at least one)
```env
OPENAI_API_KEY
ANTHROPIC_API_KEY
GOOGLE_API_KEY
GROQ_API_KEY
MISTRAL_API_KEY
DEEPSEEK_API_KEY
OPENROUTER_API_KEY
XAI_API_KEY
```

### AI Provider Endpoints
```env
OLLAMA_API_BASE
OPENAI_COMPATIBLE_BASE_URL
AZURE_OPENAI_ENDPOINT
GEMINI_API_BASE_URL
```

### Database
```env
SURREAL_URL
SURREAL_USER
SURREAL_PASSWORD
SURREAL_NAMESPACE
SURREAL_DATABASE
```

### Performance
```env
SURREAL_COMMANDS_MAX_TASKS
SURREAL_COMMANDS_RETRY_ENABLED
SURREAL_COMMANDS_RETRY_MAX_ATTEMPTS
SURREAL_COMMANDS_RETRY_WAIT_STRATEGY
SURREAL_COMMANDS_RETRY_WAIT_MIN
SURREAL_COMMANDS_RETRY_WAIT_MAX
```

### API Settings
```env
API_URL
INTERNAL_API_URL
API_CLIENT_TIMEOUT
ESPERANTO_LLM_TIMEOUT
```

### Audio/TTS
```env
ELEVENLABS_API_KEY
TTS_BATCH_SIZE
```

### Debugging
```env
LANGCHAIN_TRACING_V2
LANGCHAIN_ENDPOINT
LANGCHAIN_API_KEY
LANGCHAIN_PROJECT
```

---

## Testing Configuration

### Quick Test

```bash
# Add test config
export OPENAI_API_KEY=sk-test-key
export API_URL=http://localhost:5055

# Test connection
curl http://localhost:5055/health

# Test with sample
curl -X POST http://localhost:5055/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"Hello"}'
```

### Validate Config

```bash
# Check environment variables are set
env | grep OPENAI_API_KEY

# Verify database connection
python -c "import os; print(os.getenv('SURREAL_URL'))"
```

---

## Troubleshooting Performance

### High Memory Usage

```env
# Reduce concurrency
SURREAL_COMMANDS_MAX_TASKS=2

# Reduce TTS batch size
TTS_BATCH_SIZE=1
```

### High CPU Usage

```env
# Check worker count
SURREAL_COMMANDS_MAX_TASKS

# Reduce if maxed out:
SURREAL_COMMANDS_MAX_TASKS=5
```

### Slow Responses

```env
# Check timeout settings
API_CLIENT_TIMEOUT=300

# Check retry config
SURREAL_COMMANDS_RETRY_MAX_ATTEMPTS=3
```

### Database Conflicts

```env
# Reduce concurrency
SURREAL_COMMANDS_MAX_TASKS=3

# Use jitter strategy
SURREAL_COMMANDS_RETRY_WAIT_STRATEGY=exponential_jitter
```

---

## Backup & Restore

### Data Locations

| Path | Contents |
|------|----------|
| `./data` or `/app/data` | Uploads, podcasts, checkpoints |
| `./surreal_data` or `/mydata` | SurrealDB database files |

### Quick Backup

```bash
# Stop services (recommended for consistency)
docker compose down

# Create timestamped backup
tar -czf backup-$(date +%Y%m%d-%H%M%S).tar.gz \
  notebook_data/ surreal_data/

# Restart services
docker compose up -d
```

### Automated Backup Script

```bash
#!/bin/bash
# backup.sh - Run daily via cron

BACKUP_DIR="/path/to/backups"
DATE=$(date +%Y%m%d-%H%M%S)

# Create backup
tar -czf "$BACKUP_DIR/open-notebook-$DATE.tar.gz" \
  /path/to/notebook_data \
  /path/to/surreal_data

# Keep only last 7 days
find "$BACKUP_DIR" -name "open-notebook-*.tar.gz" -mtime +7 -delete

echo "Backup complete: open-notebook-$DATE.tar.gz"
```

Add to cron:
```bash
# Daily backup at 2 AM
0 2 * * * /path/to/backup.sh >> /var/log/open-notebook-backup.log 2>&1
```

### Restore

```bash
# Stop services
docker compose down

# Remove old data (careful!)
rm -rf notebook_data/ surreal_data/

# Extract backup
tar -xzf backup-20240115-120000.tar.gz

# Restart services
docker compose up -d
```

### Migration Between Servers

```bash
# On source server
docker compose down
tar -czf open-notebook-migration.tar.gz notebook_data/ surreal_data/

# Transfer to new server
scp open-notebook-migration.tar.gz user@newserver:/path/

# On new server
tar -xzf open-notebook-migration.tar.gz
docker compose up -d
```

---

## Container Management

### Common Commands

```bash
# Start services
docker compose up -d

# Stop services
docker compose down

# View logs (all services)
docker compose logs -f

# View logs (specific service)
docker compose logs -f api

# Restart specific service
docker compose restart api

# Update to latest version
docker compose down
docker compose pull
docker compose up -d

# Check resource usage
docker stats

# Check service health
docker compose ps
```

### Clean Up

```bash
# Remove stopped containers
docker compose rm

# Remove unused images
docker image prune

# Full cleanup (careful!)
docker system prune -a
```

---

## Summary

**Most deployments need:**
- One AI provider API key
- Default database settings
- Default timeouts

**Tune performance only if:**
- You have specific bottlenecks
- High-concurrency workload
- Custom hardware (very fast or very slow)

**Advanced features:**
- Firecrawl for better web scraping
- LangSmith for debugging workflows
- Custom CA bundles for self-signed certs
