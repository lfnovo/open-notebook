# Debugging and Diagnostics

This guide provides comprehensive debugging techniques, log analysis methods, and performance profiling tools for Open Notebook.

## Log Analysis

### Understanding Log Levels

Open Notebook uses structured logging with the following levels:
- `DEBUG`: Detailed information for debugging
- `INFO`: General information about system operation
- `WARNING`: Potentially problematic situations
- `ERROR`: Error events that might still allow the application to continue
- `CRITICAL`: Serious errors that may cause the application to abort

### Accessing Logs

#### Docker Deployment
```bash
# View all service logs
docker compose logs

# Follow logs in real-time
docker compose logs -f

# View logs for specific service
docker compose logs surrealdb
docker compose logs open_notebook

# View last 100 lines
docker compose logs --tail=100

# View logs with timestamps
docker compose logs -t
```

#### Source Installation
```bash
# API logs (if running in background)
tail -f api.log

# Worker logs
tail -f worker.log

# Database logs
docker compose logs surrealdb

# Next.js logs (stdout)
# Run in foreground to see logs directly
```

### Log Configuration

#### Enable Debug Logging
```bash
# Add to .env or docker.env
LOG_LEVEL=DEBUG

# Restart services
docker compose restart
```

#### Custom Log Configuration
```python
# For development, add to your Python code
import logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

### Common Log Messages

#### Successful Operations
```
INFO - Starting Open Notebook services
INFO - Database connection established
INFO - API server started on port 5055
INFO - React frontend started on port 8502
INFO - Background worker started
INFO - Model configuration loaded
INFO - Source processed successfully
```

#### Warning Messages
```
WARNING - Rate limit approaching for provider: openai
WARNING - Large file upload detected: 50MB
WARNING - Model response truncated due to length
WARNING - Database connection retrying
WARNING - Cache miss for embedding
```

#### Error Messages
```
ERROR - Failed to connect to database: Connection refused
ERROR - API key invalid for provider: openai
ERROR - Model not found: gpt-4-invalid
ERROR - File processing failed: Unsupported format
ERROR - Background job failed: Timeout
ERROR - Memory limit exceeded
```

## Error Diagnosis

### Database Connection Errors

#### Symptoms
```
ERROR - Database connection failed
ERROR - Connection refused at localhost:8000
ERROR - Authentication failed for SurrealDB
```

#### Diagnosis Steps
1. **Check SurrealDB status**:
   ```bash
   docker compose ps surrealdb
   ```

2. **Verify connection settings**:
   ```bash
   # Check environment variables
   echo $SURREAL_URL
   echo $SURREAL_USER
   echo $SURREAL_PASSWORD
   ```

3. **Test direct connection**:
   ```bash
   curl http://localhost:8000/health
   ```

4. **Check database logs**:
   ```bash
   docker compose logs surrealdb
   ```

#### Common Solutions
- Restart SurrealDB container
- Check port availability
- Verify credentials
- Check file permissions for data directory

### AI Provider Errors

#### API Key Issues
```
ERROR - Invalid API key for provider: openai
ERROR - Authentication failed: API key not found
ERROR - Insufficient credits for provider: anthropic
```

**Diagnosis**:
```bash
# Test OpenAI key
curl -H "Authorization: Bearer $OPENAI_API_KEY" \
     https://api.openai.com/v1/models

# Test Anthropic key
curl -H "x-api-key: $ANTHROPIC_API_KEY" \
     https://api.anthropic.com/v1/models
```

#### Model Not Found
```
ERROR - Model not found: gpt-4-invalid
ERROR - Model not available for your account
```

**Diagnosis**:
- Check model name spelling
- Verify model availability for your account
- Check provider documentation for exact model names

#### Rate Limiting
```
ERROR - Rate limit exceeded for provider: openai
ERROR - Too many requests, please retry later
```

**Diagnosis**:
```bash
# Check rate limits in provider dashboard
# Monitor request frequency
# Implement retry logic with backoff
```

### File Processing Errors

#### Upload Issues
```
ERROR - File upload failed: File too large
ERROR - Unsupported file type: .xyz
ERROR - File processing timeout
```

**Diagnosis**:
1. **Check file size**:
   ```bash
   ls -lh /path/to/file
   ```

2. **Verify file type**:
   ```bash
   file /path/to/file
   ```

3. **Test with smaller file**:
   - Use minimal test file
   - Gradually increase complexity

#### Processing Failures
```
ERROR - PDF extraction failed: Encrypted file
ERROR - Audio transcription failed: Unsupported codec
ERROR - Image OCR failed: Invalid image format
```

**Diagnosis**:
- Check file integrity
- Verify file format compliance
- Test with known good files

### Memory and Performance Issues

#### Out of Memory
```
ERROR - Out of memory: Cannot allocate
ERROR - Process killed due to memory limit
ERROR - Docker container OOMKilled
```

**Diagnosis**:
```bash
# Check memory usage
docker stats

# Check system memory
free -h

# Check Docker memory limits
docker system info | grep Memory
```

#### Performance Degradation
```
WARNING - Response time exceeded threshold: 30s
WARNING - High CPU usage detected: 95%
WARNING - Database query slow: 5s
```

**Diagnosis**:
```bash
# Monitor resources
htop
iostat -x 1

# Check database performance
docker compose logs surrealdb | grep -i slow
```

## Performance Profiling

### System Resource Monitoring

#### Real-time Monitoring
```bash
# Docker container resources
docker stats

# System resources
htop

# Disk I/O
iostat -x 1

# Network usage
nethogs
```

#### Historical Analysis
```bash
# Container resource history
docker logs --since="1h" container_name | grep -i memory

# System logs
journalctl -u docker --since="1 hour ago"
```

### Application Performance

#### Response Time Analysis
```bash
# Measure API response times
time curl http://localhost:5055/api/notebooks

# Measure with verbose output
curl -w "@curl-format.txt" http://localhost:5055/api/notebooks
```

Create `curl-format.txt`:
```
     time_namelookup:  %{time_namelookup}\n
        time_connect:  %{time_connect}\n
     time_appconnect:  %{time_appconnect}\n
    time_pretransfer:  %{time_pretransfer}\n
       time_redirect:  %{time_redirect}\n
  time_starttransfer:  %{time_starttransfer}\n
                     ----------\n
          time_total:  %{time_total}\n
```

#### Database Performance
```bash
# Check database query performance
docker compose logs surrealdb | grep -i "slow\|performance\|query"

# Monitor database connections
docker compose exec surrealdb ps aux
```

#### Memory Profiling
```python
# Add to Python code for memory profiling
import tracemalloc
tracemalloc.start()

# Your code here

current, peak = tracemalloc.get_traced_memory()
print(f"Current memory usage: {current / 1024 / 1024:.1f} MB")
print(f"Peak memory usage: {peak / 1024 / 1024:.1f} MB")
tracemalloc.stop()
```

### AI Provider Performance

#### Response Time Monitoring
```bash
# Monitor AI provider response times
grep -r "provider.*response_time" logs/

# Check for timeouts
grep -r "timeout\|Timeout" logs/
```

#### Usage Analytics
```python
# Track AI usage patterns
# Add to your monitoring code
import time
start_time = time.time()

# AI API call here

end_time = time.time()
response_time = end_time - start_time
print(f"AI response time: {response_time:.2f}s")
```

## Support Information Gathering

### System Information Collection

#### Basic System Info
```bash
# System details
uname -a
lsb_release -a  # Linux
sw_vers  # macOS

# Docker information
docker version
docker compose version
docker system info
```

#### Open Notebook Information
```bash
# Version information
grep version pyproject.toml

# Service status
make status

# Environment check (without sensitive info)
env | grep -E "(SURREAL|LOG|DEBUG)" | grep -v "PASSWORD\|KEY"
```

### Log Collection for Support

#### Comprehensive Log Collection
```bash
#!/bin/bash
# collect_logs.sh

echo "Collecting Open Notebook diagnostic information..."

# Create diagnostic directory
mkdir -p diagnostic_$(date +%Y%m%d_%H%M%S)
cd diagnostic_$(date +%Y%m%d_%H%M%S)

# System information
echo "Collecting system information..."
uname -a > system_info.txt
docker version >> system_info.txt
docker compose version >> system_info.txt

# Service status
echo "Collecting service status..."
make status > service_status.txt
docker compose ps >> service_status.txt

# Logs
echo "Collecting logs..."
docker compose logs --tail=500 > docker_logs.txt
docker compose logs surrealdb --tail=200 > surrealdb_logs.txt

# Configuration (sanitized)
echo "Collecting configuration..."
env | grep -E "(SURREAL|LOG|DEBUG)" | grep -v "PASSWORD\|KEY" > environment.txt

# Resource usage
echo "Collecting resource information..."
docker stats --no-stream > resource_usage.txt
df -h > disk_usage.txt
free -h > memory_info.txt

echo "Diagnostic collection complete!"
echo "Please compress and share the diagnostic_* directory"
```

#### Sanitizing Logs
```bash
# Remove sensitive information from logs
sed -i 's/sk-[a-zA-Z0-9]*/[REDACTED_API_KEY]/g' logs.txt
sed -i 's/password=[^[:space:]]*/password=[REDACTED]/g' logs.txt
```

### Creating Reproduction Cases

#### Minimal Reproduction
1. **Start with clean environment**:
   ```bash
   # Fresh installation
   rm -rf surreal_data/ notebook_data/
   docker compose down
   docker compose up -d
   ```

2. **Document exact steps**:
   - Each click or command
   - Exact file used
   - Configuration settings
   - Expected vs actual behavior

3. **Capture evidence**:
   - Screenshots of errors
   - Full error messages
   - Log excerpts
   - System state

#### Test Case Template
```markdown
## Bug Report

### Environment
- OS: [e.g., Ubuntu 22.04]
- Docker version: [e.g., 24.0.7]
- Open Notebook version: [e.g., 1.0.0]
- Installation method: [Docker/Source]

### Steps to Reproduce
1. Start Open Notebook
2. Create new notebook named "Test"
3. Add text source: "Hello world"
4. Navigate to Chat
5. Ask: "What is this about?"

### Expected Behavior
Should receive response about the text content

### Actual Behavior
Error: "Model not found"

### Logs
```
ERROR - Model not found: gpt-4-invalid
```

### Additional Context
- Using OpenAI provider
- gpt-5-mini model configured
- First time setup
```

## Advanced Debugging

### Database Debugging

#### Direct Database Access
```bash
# Connect to SurrealDB directly
docker compose exec surrealdb /surreal sql \
  --conn http://localhost:8000 \
  --user root \
  --pass root \
  --ns open_notebook \
  --db production
```

#### Query Analysis
```sql
-- Check table contents
SELECT * FROM notebook LIMIT 10;

-- Check relationships
SELECT * FROM source WHERE notebook_id = notebook:abc123;

-- Performance analysis
SELECT count() FROM source GROUP BY notebook_id;
```

### Network Debugging

#### Service Communication
```bash
# Test internal Docker network
docker compose exec open_notebook ping surrealdb

# Test external connectivity
docker compose exec open_notebook curl -I https://api.openai.com

# Check port bindings
netstat -tulpn | grep -E "(8000|5055|8502)"
```

#### DNS Resolution
```bash
# Check DNS from container
docker compose exec open_notebook nslookup api.openai.com

# Check /etc/hosts
docker compose exec open_notebook cat /etc/hosts
```

### Performance Debugging

#### CPU Profiling
```python
# Add to Python code
import cProfile
import pstats

# Profile your function
cProfile.run('your_function()', 'profile_stats')

# Analyze results
p = pstats.Stats('profile_stats')
p.sort_stats('cumulative').print_stats(10)
```

#### Memory Leak Detection
```python
# Track memory usage over time
import psutil
import os

def log_memory_usage():
    process = psutil.Process(os.getpid())
    memory_mb = process.memory_info().rss / 1024 / 1024
    print(f"Memory usage: {memory_mb:.1f} MB")

# Call periodically
log_memory_usage()
```

## Monitoring and Alerting

### Health Checks

#### Service Health Endpoints
```bash
# Check all health endpoints
curl -f http://localhost:8000/health  # SurrealDB
curl -f http://localhost:5055/health  # API
curl -f http://localhost:8502/healthz  # Next.js
```

#### Automated Health Monitoring
```bash
#!/bin/bash
# health_check.sh

services=("8000" "5055" "8502")
for port in "${services[@]}"; do
    if curl -f http://localhost:$port/health* >/dev/null 2>&1; then
        echo "✅ Service on port $port is healthy"
    else
        echo "❌ Service on port $port is unhealthy"
    fi
done
```

### Log Monitoring

#### Real-time Error Monitoring
```bash
# Monitor for errors in real-time
docker compose logs -f | grep -i error

# Monitor specific patterns
docker compose logs -f | grep -E "(ERROR|CRITICAL|timeout)"
```

#### Log Analysis Scripts
```bash
#!/bin/bash
# analyze_logs.sh

echo "Error Summary:"
docker compose logs --since="1h" | grep -c "ERROR"

echo "Top Error Messages:"
docker compose logs --since="1h" | grep "ERROR" | \
  cut -d':' -f4- | sort | uniq -c | sort -nr | head -10

echo "Provider Issues:"
docker compose logs --since="1h" | grep -i "provider.*error"
```

## Best Practices for Debugging

### Systematic Approach
1. **Reproduce the issue** consistently
2. **Isolate the problem** to specific components
3. **Check recent changes** that might have caused issues
4. **Gather evidence** through logs and monitoring
5. **Test hypotheses** systematically
6. **Document findings** for future reference

### Debugging Tools Checklist
- [ ] System resource monitoring (htop, docker stats)
- [ ] Log aggregation and analysis
- [ ] Network connectivity testing
- [ ] Database query analysis
- [ ] API response time measurement
- [ ] Memory usage tracking
- [ ] Error rate monitoring

### When to Seek Help
- Issue persists after following troubleshooting guides
- Problem affects multiple users or systems
- Security-related concerns
- Performance degradation without clear cause
- Data integrity issues

---

*This debugging guide is continuously updated based on real-world troubleshooting experiences. For additional support, join our Discord community or create a GitHub issue with your diagnostic information.*