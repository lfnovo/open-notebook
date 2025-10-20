# Common Issues and Solutions

This document covers the most frequently encountered issues when installing, configuring, and using Open Notebook, along with their solutions.

> **🆘 Quick Fixes for Setup Issues**
>
> Most problems are caused by incorrect API_URL configuration. Choose your scenario below for instant fixes.

## Setup-Related Issues (START HERE!)

### ❌ "Unable to connect to server" or "Connection Error"

**This is the #1 issue for new users.** The frontend can't reach the API.

#### Diagnostic Checklist:

1. **Are both ports exposed?**
   ```bash
   docker ps
   # Should show: 0.0.0.0:8502->8502 AND 0.0.0.0:5055->5055
   ```
   ✅ **Fix:** Add `-p 5055:5055` to your docker run command, or add it to docker-compose.yml:
   ```yaml
   ports:
     - "8502:8502"
     - "5055:5055"  # Add this!
   ```

2. **Are you accessing from a different machine than where Docker is running?**

   **Determine your server's IP:**
   ```bash
   # On the Docker host machine:
   hostname -I          # Linux
   ipconfig             # Windows
   ifconfig | grep inet # Mac
   ```

   ✅ **Fix:** Set environment variable (replace with your actual server IP):

   **Docker Compose:**
   ```yaml
   environment:
     - API_URL=http://192.168.1.100:5055
   ```

   **Docker Run:**
   ```bash
   -e API_URL=http://192.168.1.100:5055
   ```

3. **Using localhost in API_URL but accessing remotely?**

   ❌ **Wrong:**
   ```
   Access from browser: http://192.168.1.100:8502
   API_URL setting: http://localhost:5055  # This won't work!
   ```

   ✅ **Correct:**
   ```
   Access from browser: http://192.168.1.100:8502
   API_URL setting: http://192.168.1.100:5055
   ```

#### Common Scenarios:

| Your Setup | Access URL | API_URL Value |
|------------|-----------|---------------|
| Docker on your laptop, accessed locally | `http://localhost:8502` | Not needed (or `http://localhost:5055`) |
| Docker on Proxmox VM at 192.168.1.50 | `http://192.168.1.50:8502` | `http://192.168.1.50:5055` |
| Docker on Raspberry Pi at 10.0.0.10 | `http://10.0.0.10:8502` | `http://10.0.0.10:5055` |
| Docker on NAS at nas.local | `http://nas.local:8502` | `http://nas.local:5055` |
| Behind reverse proxy at notebook.mydomain.com | `https://notebook.mydomain.com` | `https://notebook.mydomain.com/api` |

#### After changing API_URL:

**Always restart the container:**
```bash
# Docker Compose
docker compose down
docker compose up -d

# Docker Run
docker stop open-notebook
docker rm open-notebook
# Then run your docker run command again
```

---

### ❌ Frontend trying to connect on port 8502 instead of 5055

**Symptom:** Frontend tries to access `http://10.10.10.107:8502/api/config` instead of using port 5055.

**Cause:** API_URL is not set correctly or you're using an old version.

✅ **Fix:**
1. Ensure you're using version 1.0.6+ which supports runtime API_URL
2. Set API_URL environment variable (not NEXT_PUBLIC_API_URL)
3. Restart container after setting the variable
   ```bash
   docker compose down && docker compose up -d
   ```

---

### ❌ "API config endpoint returned status 404"

**Cause:** You added `/api` to the end of API_URL.

❌ **Wrong:** `API_URL=http://192.168.1.100:5055/api`

✅ **Correct:** `API_URL=http://192.168.1.100:5055`

The `/api` path is added automatically by the application.

---

### ❌ "Missing authorization header"

**Cause:** You have password authentication enabled but it's not configured correctly.

✅ **Fix:** Set the password in your environment:
```yaml
environment:
  - OPEN_NOTEBOOK_PASSWORD=your_secure_password
```

Or provide it when logging into the web interface.

---

## Installation Problems

### Port Already in Use

**Problem**: Error message "Port 8502 is already in use" or similar port conflicts.

**Symptoms**:
- Cannot start React frontend
- Error messages about address already in use
- Services failing to bind to ports

**Solutions**:

1. **Find and stop conflicting process**:
   ```bash
   # Check what's using port 8502
   lsof -i :8502
   
   # Kill the process (replace PID with actual process ID)
   kill -9 <PID>
   ```

2. **Use different ports**:
   ```bash
   # For React frontend
   uv run --env-file .env cd frontend && npm run dev --server.port=8503
   
   # For Docker deployment, modify docker-compose.yml
   ports:
     - "8503:8502"  # host:container
   ```

3. **Common port conflicts**:
   - Port 8502 (Next.js): Often used by other Next.js apps
   - Port 5055 (API): May conflict with other web services
   - Port 8000 (SurrealDB): May conflict with other databases

### Permission Denied (Docker)

**Problem**: Docker commands fail with permission denied errors.

**Symptoms**:
- "permission denied while trying to connect to the Docker daemon socket"
- Docker commands require sudo

**Solutions**:

1. **Add user to docker group (Linux)**:
   ```bash
   sudo usermod -aG docker $USER
   
   # Log out and log back in, or run:
   newgrp docker
   ```

2. **Start Docker service (Linux)**:
   ```bash
   sudo systemctl start docker
   sudo systemctl enable docker
   ```

3. **Restart Docker Desktop (Windows/Mac)**:
   - Close Docker Desktop completely
   - Restart Docker Desktop
   - Wait for it to fully start

### Python/uv Installation Issues

**Problem**: `uv` command not found or Python version conflicts.

**Symptoms**:
- "uv: command not found"
- Python version mismatch errors
- Virtual environment issues

**Solutions**:

1. **Install uv package manager**:
   ```bash
   # macOS
   brew install uv
   
   # Linux/WSL
   curl -LsSf https://astral.sh/uv/install.sh | sh
   source ~/.bashrc
   
   # Windows
   powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
   ```

2. **Fix Python version issues**:
   ```bash
   # Install specific Python version
   uv python install 3.11
   
   # Pin Python version for project
   uv python pin 3.11
   
   # Recreate virtual environment
   uv sync --reinstall
   ```

3. **Clear uv cache**:
   ```bash
   uv cache clean
   ```

### SurrealDB Connection Issues

**Problem**: Cannot connect to SurrealDB database.

**Symptoms**:
- "Connection refused" errors
- Database queries failing
- Timeout errors

**Solutions**:

1. **Check SurrealDB is running**:
   ```bash
   # For Docker
   docker compose ps surrealdb
   
   # Check logs
   docker compose logs surrealdb
   ```

2. **Verify connection settings**:
   ```bash
   # Check environment variables
   echo $SURREAL_URL
   echo $SURREAL_USER
   
   # Test connection
   curl http://localhost:8000/health
   ```

3. **Restart SurrealDB**:
   ```bash
   docker compose restart surrealdb
   # Wait 10 seconds for startup
   sleep 10
   ```

4. **Check file permissions**:
   ```bash
   # Ensure data directory is writable
   ls -la surreal_data/
   
   # Fix permissions if needed
   sudo chown -R $USER:$USER surreal_data/
   ```

## Runtime Errors

### AI Provider API Errors

**Problem**: Errors when using AI models (OpenAI, Anthropic, etc.).

**Symptoms**:
- "Invalid API key" errors
- "Rate limit exceeded" messages
- Model not found errors

**Solutions**:

1. **Verify API keys**:
   ```bash
   # Check key format (don't expose full key)
   echo $OPENAI_API_KEY | cut -c1-10
   
   # Test OpenAI key
   curl -H "Authorization: Bearer $OPENAI_API_KEY" \
        https://api.openai.com/v1/models
   ```

2. **Check billing and usage**:
   - OpenAI: Visit https://platform.openai.com/account/billing
   - Anthropic: Visit https://console.anthropic.com/account/billing
   - Ensure you have sufficient credits

3. **Verify model availability**:
   ```bash
   # Check model names in settings
   # Use gpt-5-mini instead of gpt-4-mini
   # Use claude-3-haiku-20240307 instead of claude-3-haiku
   ```

4. **Handle rate limits**:
   - Wait before retrying
   - Use lower-tier models for testing
   - Check provider rate limits

### API Timeout Errors During Transformations

**Problem**: Timeout errors when running transformations or generating insights, even though the operation completes successfully.

**Symptoms**:
- "timeout of 30000ms exceeded" in React frontend
- "Failed to connect to API: timed out" in Streamlit UI
- Transformation completes after a few minutes, but error appears after 30-60 seconds
- Common with local models (Ollama), remote LM Studio, or slow hardware

**Solutions**:

1. **Increase API client timeout** (recommended):
   ```bash
   # Add to your .env file
   API_CLIENT_TIMEOUT=600  # 10 minutes (600 seconds)
   ```

   This controls how long the frontend/UI waits for API responses. Default is 300 seconds (5 minutes).

2. **Adjust timeout based on your setup**:
   ```bash
   # Fast cloud APIs (OpenAI, Anthropic, Groq)
   API_CLIENT_TIMEOUT=300  # 5 minutes (default)

   # Local Ollama on GPU
   API_CLIENT_TIMEOUT=600  # 10 minutes

   # Local Ollama on CPU or slow hardware
   API_CLIENT_TIMEOUT=1200  # 20 minutes

   # Remote LM Studio over slow network
   API_CLIENT_TIMEOUT=900  # 15 minutes
   ```

3. **Increase LLM provider timeout if needed**:
   ```bash
   # Add to your .env file if the model itself is timing out
   ESPERANTO_LLM_TIMEOUT=180  # 3 minutes (default is 60s)
   ```

   Only increase this if you see errors during actual model inference, not just HTTP timeouts.

4. **Use faster models for testing**:
   - Test with cloud APIs first to verify setup
   - Try smaller local models (e.g., `gemma2:2b` instead of `llama3:70b`)
   - Preload models before running transformations: `ollama run model-name`

5. **Restart services after configuration changes**:
   ```bash
   # For Docker
   docker compose down
   docker compose up -d

   # For source installation
   make stop-all
   make start-all
   ```

**Important Notes**:
- `API_CLIENT_TIMEOUT` should be HIGHER than `ESPERANTO_LLM_TIMEOUT` for proper error handling
- If transformations complete successfully after refresh, you only need to increase `API_CLIENT_TIMEOUT`
- First time running a model may be slower due to model loading

**Related GitHub Issue**: [#131](https://github.com/lfnovo/open-notebook/issues/131)

### Memory and Performance Issues

**Problem**: Application running slowly or crashing due to memory issues.

**Symptoms**:
- Slow response times
- Out of memory errors
- Application crashes
- High CPU usage

**Solutions**:

1. **Increase Docker memory**:
   ```bash
   # Docker Desktop → Settings → Resources → Memory
   # Increase to 4GB or more
   ```

2. **Monitor resource usage**:
   ```bash
   # Check Docker stats
   docker stats
   
   # Check system resources
   htop
   top
   ```

3. **Optimize model usage**:
   - Use smaller models (gpt-5-mini vs gpt-5)
   - Reduce context window size
   - Process fewer documents at once

4. **Clear application cache**:
   ```bash
   # Clear Python cache
   find . -name "__pycache__" -type d -exec rm -rf {} +
   
   # Clear Next.js cache
   rm -rf ~/.streamlit/cache/
   ```

### Background Job Failures

**Problem**: Background tasks (podcast generation, transformations) failing.

**Symptoms**:
- Jobs stuck in "processing" state
- No podcast audio generated
- Transformations not completing

**Solutions**:

1. **Check worker status**:
   ```bash
   # Check if worker is running
   pgrep -f "surreal-commands-worker"
   
   # Restart worker
   make worker-restart
   ```

2. **Check job logs**:
   ```bash
   # View worker logs
   docker compose logs worker
   
   # Check command status in database
   # (Access through UI or API)
   ```

3. **Verify AI provider configuration**:
   - Ensure TTS/STT models are configured
   - Check API keys for required providers
   - Test models individually

4. **Clear stuck jobs**:
   ```bash
   # Restart all services
   make stop-all
   make start-all
   ```

### File Upload Issues

**Problem**: Cannot upload files or file processing fails.

**Symptoms**:
- Upload button not working
- File processing errors
- Unsupported file type messages

**Solutions**:

1. **Check file size limits**:
   ```bash
   # Default Next.js limit is 200MB
   # Large files may timeout
   ```

2. **Verify file types**:
   - PDF: Standard PDF files (not password protected)
   - Images: PNG, JPG, GIF, WebP
   - Audio: MP3, WAV, M4A
   - Video: MP4, AVI, MOV (for transcript extraction)
   - Documents: TXT, DOC, DOCX

3. **Check file permissions**:
   ```bash
   # Ensure files are readable
   ls -la /path/to/file
   
   # Fix permissions
   chmod 644 /path/to/file
   ```

4. **Test with smaller files**:
   - Try with a simple text file first
   - Gradually increase complexity

## Performance Issues

### Slow Search and Chat

**Problem**: Search and chat responses are very slow.

**Symptoms**:
- Long wait times for responses
- Timeout errors
- Poor user experience

**Solutions**:

1. **Optimize embedding model**:
   - Use faster embedding models
   - Reduce embedding dimensions
   - Process fewer documents at once

2. **Database optimization**:
   ```bash
   # Check database performance
   docker compose logs surrealdb
   
   # Consider using RocksDB for better performance
   # (Already configured in docker-compose.yml)
   ```

3. **Reduce context size**:
   - Limit search results
   - Use shorter prompts
   - Reduce notebook size

4. **Use faster models**:
   - gpt-5-mini instead of gpt-5
   - claude-3-haiku instead of claude-3-opus
   - Local models for simple tasks

### High Resource Usage

**Problem**: Application consuming too much CPU or memory.

**Symptoms**:
- High CPU usage in task manager
- System becoming unresponsive
- Docker containers using excessive resources

**Solutions**:

1. **Set resource limits**:
   ```yaml
   # In docker-compose.yml
   services:
     open_notebook:
       deploy:
         resources:
           limits:
             memory: 2G
             cpus: "1.0"
   ```

2. **Monitor and identify bottlenecks**:
   ```bash
   # Check which service is consuming resources
   docker stats
   
   # Check system processes
   htop
   ```

3. **Optimize processing**:
   - Process documents in batches
   - Use background jobs for heavy tasks
   - Limit concurrent operations

## Configuration Problems

### Environment Variables Not Loading

**Problem**: Environment variables are not being read correctly.

**Symptoms**:
- Default values being used instead of configured values
- API keys not recognized
- Connection errors to external services

**Solutions**:

1. **Check file names**:
   ```bash
   # For source installation
   ls -la .env
   
   # For Docker
   ls -la docker.env
   ```

2. **Verify file format**:
   ```bash
   # Check for invisible characters
   cat -A .env
   
   # Ensure no spaces around equals
   OPENAI_API_KEY=value  # Correct
   OPENAI_API_KEY = value  # Incorrect
   ```

3. **Check environment loading**:
   ```bash
   # Test environment variable
   echo $OPENAI_API_KEY
   
   # For Docker
   docker compose config
   ```

4. **Restart services after changes**:
   ```bash
   # For Docker
   docker compose down
   docker compose up -d
   
   # For source installation
   make stop-all
   make start-all
   ```

### Model Configuration Issues

**Problem**: AI models not working or configured incorrectly.

**Symptoms**:
- Model not found errors
- Incorrect responses
- Configuration not saving

**Solutions**:

1. **Check model names**:
   ```bash
   # Use exact model names from provider documentation
   # OpenAI: gpt-5-mini, gpt-5, text-embedding-3-small
   # Anthropic: claude-3-haiku-20240307, claude-3-sonnet-20240229
   ```

2. **Verify provider configuration**:
   - Check API keys are valid
   - Ensure models are available for your account
   - Test with simple requests first

3. **Reset model configuration**:
   - Go to Models
   - Clear all configurations
   - Reconfigure with known working models

4. **Check provider status**:
   - Visit provider status pages
   - Check for service outages
   - Try alternative providers

### Database Schema Issues

**Problem**: Database schema conflicts or migration issues.

**Symptoms**:
- Field validation errors
- Query failures
- Data not saving correctly

**Solutions**:

1. **Check database logs**:
   ```bash
   docker compose logs surrealdb
   ```

2. **Reset database (WARNING: This deletes all data)**:
   ```bash
   # Stop services
   make stop-all
   
   # Remove database files
   rm -rf surreal_data/
   
   # Restart services (will recreate database)
   make start-all
   ```

3. **Manual schema update**:
   ```bash
   # Run migrations
   uv run python -m open_notebook.database.async_migrate
   ```

4. **Check SurrealDB version**:
   ```bash
   # Ensure using compatible version
   docker compose pull surrealdb
   docker compose up -d
   ```

## Getting Help

If you've tried the solutions above and are still experiencing issues:

1. **Collect diagnostic information**:
   ```bash
   # System information
   uname -a
   docker version
   docker compose version
   
   # Service status
   make status
   
   # Recent logs
   docker compose logs --tail=100 > logs.txt
   ```

2. **Create a minimal reproduction**:
   - Start with a fresh installation
   - Use minimal configuration
   - Document exact steps to reproduce

3. **Ask for help**:
   - Discord: https://discord.gg/37XJPXfz2w
   - GitHub Issues: https://github.com/lfnovo/open-notebook/issues
   - Include all diagnostic information

Remember to remove API keys and sensitive information before sharing logs or configuration files.