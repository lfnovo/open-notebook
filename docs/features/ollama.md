# Ollama Setup Guide

Ollama provides free, local AI models that run on your own hardware. This guide covers everything you need to know about setting up Ollama with Open Notebook, including different deployment scenarios and network configurations.

## Why Choose Ollama?

- **🆓 Completely Free**: No API costs after initial setup
- **🔒 Full Privacy**: Your data never leaves your local network
- **📱 Offline Capable**: Works without internet connection
- **🚀 Fast**: Local inference with no network latency
- **🧠 Reasoning Models**: Support for advanced reasoning models like DeepSeek-R1
- **💾 Model Variety**: Access to hundreds of open-source models

## Quick Start

### 1. Install Ollama

**Linux/macOS:**
```bash
curl -fsSL https://ollama.ai/install.sh | sh
```

**Windows:**
Download and install from [ollama.ai](https://ollama.ai/download)

### 2. Pull Required Models

```bash
# Language models (choose one or more)
ollama pull qwen3              # Excellent general purpose, 7B parameters
ollama pull gemma3            # Google's model, good performance
ollama pull deepseek-r1       # Advanced reasoning model
ollama pull phi4              # Microsoft's efficient model

# Embedding model (required for search)
ollama pull mxbai-embed-large  # Best embedding model for Ollama
```

### 3. Configure Open Notebook

**For local installation:**
```bash
export OLLAMA_API_BASE=http://localhost:11434
```

**For Docker installation:**
```bash
export OLLAMA_API_BASE=http://host.docker.internal:11434
```

## Network Configuration Guide

The `OLLAMA_API_BASE` environment variable tells Open Notebook where to find your Ollama server. The correct value depends on your deployment scenario:

### Scenario 1: Local Installation (Same Machine)

When both Open Notebook and Ollama run directly on your machine:

```bash
export OLLAMA_API_BASE=http://localhost:11434
# or
export OLLAMA_API_BASE=http://127.0.0.1:11434
```

**Use `localhost` vs `127.0.0.1`:**
- **localhost**: Recommended, works with most configurations
- **127.0.0.1**: Use if you have DNS resolution issues with localhost

### Scenario 2: Open Notebook in Docker, Ollama on Host

When Open Notebook runs in Docker but Ollama runs on your host machine:

```bash
export OLLAMA_API_BASE=http://host.docker.internal:11434
```

**⚠️ CRITICAL: Ollama must accept external connections:**
```bash
# Start Ollama with external access enabled
export OLLAMA_HOST=0.0.0.0:11434
ollama serve
```

**Why `host.docker.internal`?**
- Docker containers can't reach `localhost` on the host
- `host.docker.internal` is Docker's special hostname for the host machine
- Available on Docker Desktop for Mac/Windows and recent Linux versions

**Why `OLLAMA_HOST=0.0.0.0:11434`?**
- By default, Ollama only binds to localhost and rejects external connections
- Docker containers are considered "external" even when running on the same machine
- Setting `OLLAMA_HOST=0.0.0.0:11434` allows connections from Docker containers

### Scenario 3: Both in Docker (Same Compose)

When both Open Notebook and Ollama run in the same Docker Compose stack:

```bash
export OLLAMA_API_BASE=http://ollama:11434
```

**Docker Compose Example:**

```yaml
version: '3.8'
services:
  open-notebook:
    image: lfnovo/open_notebook:v1-latest-single
    ports:
      - "8502:8502"
      - "5055:5055"
    environment:
      - OLLAMA_API_BASE=http://ollama:11434
    volumes:
      - ./notebook_data:/app/data
      - ./surreal_data:/mydata
    depends_on:
      - ollama

  ollama:
    image: ollama/ollama:v1-latest
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    # Optional: GPU support
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]

volumes:
  ollama_data:
```

### Scenario 4: Remote Ollama Server

When Ollama runs on a different machine in your network:

```bash
export OLLAMA_API_BASE=http://192.168.1.100:11434
# Replace 192.168.1.100 with your Ollama server's IP address
```

**Security Note:** Only use this in trusted networks. Ollama doesn't have built-in authentication.

### Scenario 5: Ollama with Custom Port

If you've configured Ollama to use a different port:

```bash
# Start Ollama on custom port
OLLAMA_HOST=0.0.0.0:8080 ollama serve

# Configure Open Notebook
export OLLAMA_API_BASE=http://localhost:8080
```

## Model Recommendations

### Language Models

| Model | Size | Best For | Quality | Speed |
|-------|------|----------|---------|-------|
| **qwen3** | 7B | General purpose, coding | Excellent | Fast |
| **deepseek-r1** | 7B | Reasoning, problem-solving | Exceptional | Medium |
| **gemma3** | 7B | Balanced performance | Very Good | Fast |
| **phi4** | 14B | Efficiency on small hardware | Good | Very Fast |
| **llama3** | 8B | General purpose | Very Good | Medium |

### Embedding Models

| Model | Best For | Performance |
|-------|----------|-------------|
| **mxbai-embed-large** | General search | Excellent |
| **nomic-embed-text** | Document similarity | Good |
| **all-minilm** | Lightweight option | Fair |

### Installation Commands

```bash
# Essential models
ollama pull qwen3                 # Primary language model
ollama pull mxbai-embed-large     # Search embeddings

# Optional reasoning model
ollama pull deepseek-r1           # Advanced reasoning

# Alternative language models
ollama pull gemma3                # Google's model
ollama pull phi4                  # Microsoft's efficient model
```

## Hardware Requirements

### Minimum Requirements
- **RAM**: 8GB (for 7B models)
- **Storage**: 10GB free space per model
- **CPU**: Modern multi-core processor

### Recommended Setup
- **RAM**: 16GB+ (for multiple models)
- **Storage**: SSD with 50GB+ free space
- **GPU**: NVIDIA GPU with 8GB+ VRAM (optional but faster)

### GPU Acceleration

**NVIDIA GPU (CUDA):**
```bash
# Install NVIDIA Container Toolkit for Docker
# Then use the Docker Compose example above with GPU support

# For local installation, Ollama auto-detects CUDA
ollama pull qwen3
```

**Apple Silicon (M1/M2/M3):**
```bash
# Ollama automatically uses Metal acceleration
# No additional setup required
ollama pull qwen3
```

**AMD GPUs:**
```bash
# ROCm support varies by model and system
# Check Ollama documentation for latest compatibility
```

## Troubleshooting

### Common Issues

**1. "Ollama unavailable" in Open Notebook**

**Check Ollama is running:**
```bash
curl http://localhost:11434/api/tags
```

**Verify environment variable:**
```bash
echo $OLLAMA_API_BASE
```

**⚠️ IMPORTANT: Enable external connections (most common fix):**
```bash
# If Open Notebook runs in Docker or on a different machine,
# Ollama must bind to all interfaces, not just localhost
export OLLAMA_HOST=0.0.0.0:11434
ollama serve
```
> **Why this is needed:** By default, Ollama only accepts connections from `localhost` (127.0.0.1). When Open Notebook runs in Docker or on a different machine, it can't reach Ollama unless you configure `OLLAMA_HOST=0.0.0.0:11434` to accept external connections.

**Restart Ollama:**
```bash
# Linux/macOS
sudo systemctl restart ollama
# or
ollama serve

# Windows
# Restart from system tray or Services
```

**2. Docker networking issues**

**From inside Open Notebook container, test Ollama:**
```bash
# Get into container
docker exec -it open-notebook bash

# Test connection
curl http://host.docker.internal:11434/api/tags
```

**3. Models not downloading**

**Check disk space:**
```bash
df -h
```

**Manual model pull:**
```bash
ollama pull qwen3 --verbose
```

**Clear failed downloads:**
```bash
ollama rm qwen3
ollama pull qwen3
```

**4. Slow performance**

**Check model size vs available RAM:**
```bash
ollama ps  # Show running models
free -h    # Check available memory
```

**Use smaller models:**
```bash
ollama pull phi4         # Instead of larger models
ollama pull gemma3:2b   # 2B parameter variant
```

**5. Port conflicts**

**Check what's using port 11434:**
```bash
lsof -i :11434
netstat -tulpn | grep 11434
```

**Use custom port:**
```bash
OLLAMA_HOST=0.0.0.0:8080 ollama serve
export OLLAMA_API_BASE=http://localhost:8080
```

### Docker-Specific Troubleshooting

**1. Host networking on Linux:**
```bash
# Use host networking if host.docker.internal doesn't work
docker run --network host lfnovo/open_notebook:v1-latest-single
export OLLAMA_API_BASE=http://localhost:11434
```

**2. Custom bridge network:**
```yaml
version: '3.8'
networks:
  ollama_network:
    driver: bridge

services:
  open-notebook:
    networks:
      - ollama_network
    environment:
      - OLLAMA_API_BASE=http://ollama:11434

  ollama:
    networks:
      - ollama_network
```

**3. Firewall issues:**
```bash
# Allow Ollama port through firewall
sudo ufw allow 11434
# or
sudo firewall-cmd --add-port=11434/tcp --permanent
```

## Performance Optimization

### Model Management

**List installed models:**
```bash
ollama list
```

**Remove unused models:**
```bash
ollama rm model_name
```

**Show running models:**
```bash
ollama ps
```

**Preload models for faster startup:**
```bash
# Keep model in memory
curl http://localhost:11434/api/generate -d '{
  "model": "qwen3",
  "prompt": "test",
  "keep_alive": -1
}'
```

### System Optimization

**Linux: Increase file limits:**
```bash
echo "* soft nofile 65536" >> /etc/security/limits.conf
echo "* hard nofile 65536" >> /etc/security/limits.conf
```

**macOS: Increase memory limits:**
```bash
# Add to ~/.zshrc or ~/.bash_profile
export OLLAMA_MAX_LOADED_MODELS=2
export OLLAMA_NUM_PARALLEL=4
```

**Docker: Resource allocation:**
```yaml
services:
  ollama:
    deploy:
      resources:
        limits:
          memory: 8G
          cpus: '4'
```

## Advanced Configuration

### Environment Variables

```bash
# Ollama server configuration
export OLLAMA_HOST=0.0.0.0:11434      # Bind to all interfaces
export OLLAMA_KEEP_ALIVE=5m            # Keep models in memory
export OLLAMA_MAX_LOADED_MODELS=3      # Max concurrent models
export OLLAMA_MAX_QUEUE=512            # Request queue size
export OLLAMA_NUM_PARALLEL=4           # Parallel request handling
export OLLAMA_FLASH_ATTENTION=1        # Enable flash attention (if supported)

# Open Notebook configuration
export OLLAMA_API_BASE=http://localhost:11434
```

### Custom Model Imports

**Import custom models:**
```bash
# Create Modelfile
cat > Modelfile << EOF
FROM qwen3
PARAMETER temperature 0.7
PARAMETER top_p 0.9
SYSTEM "You are a helpful research assistant."
EOF

# Create custom model
ollama create my-research-model -f Modelfile
```

**Use in Open Notebook:**
1. Go to Models
2. Add new model: `my-research-model`
3. Set as default for specific tasks

### Monitoring and Logging

**Monitor Ollama logs:**
```bash
# Linux (systemd)
journalctl -u ollama -f

# Docker
docker logs -f ollama

# Manual run with verbose logging
OLLAMA_DEBUG=1 ollama serve
```

**Resource monitoring:**
```bash
# CPU and memory usage
htop

# GPU usage (NVIDIA)
nvidia-smi -l 1

# Model-specific metrics
ollama ps
```

## Integration Examples

### Python Script Integration

```python
import requests
import os

# Test Ollama connection
ollama_base = os.environ.get('OLLAMA_API_BASE', 'http://localhost:11434')
response = requests.get(f'{ollama_base}/api/tags')
print(f"Available models: {response.json()}")

# Generate text
payload = {
    "model": "qwen3",
    "prompt": "Explain quantum computing",
    "stream": False
}
response = requests.post(f'{ollama_base}/api/generate', json=payload)
print(response.json()['response'])
```

### Health Check Script

```bash
#!/bin/bash
# ollama-health-check.sh

OLLAMA_API_BASE=${OLLAMA_API_BASE:-"http://localhost:11434"}

echo "Checking Ollama health..."
if curl -s "${OLLAMA_API_BASE}/api/tags" > /dev/null; then
    echo "✅ Ollama is running"
    echo "Available models:"
    curl -s "${OLLAMA_API_BASE}/api/tags" | jq -r '.models[].name'
else
    echo "❌ Ollama is not accessible at ${OLLAMA_API_BASE}"
    exit 1
fi
```

## Migration from Other Providers

### Coming from OpenAI

**Similar performance models:**
- GPT-4 → `qwen3` or `deepseek-r1`
- GPT-3.5 → `gemma3` or `phi4`
- text-embedding-ada-002 → `mxbai-embed-large`

**Cost comparison:**
- OpenAI: $0.01-0.06 per 1K tokens
- Ollama: $0 after hardware investment

### Coming from Anthropic

**Claude replacement suggestions:**
- Claude 3.5 Sonnet → `deepseek-r1` (reasoning)
- Claude 3 Haiku → `phi4` (speed)

## Best Practices

### Security

1. **Network Security:**
   - Run Ollama only on trusted networks
   - Use firewall rules to limit access
   - Consider VPN for remote access

2. **Model Verification:**
   - Only pull models from trusted sources
   - Verify model checksums when possible

3. **Resource Limits:**
   - Set memory and CPU limits in production
   - Monitor resource usage regularly

### Performance

1. **Model Selection:**
   - Use appropriate model size for your hardware
   - Smaller models for simple tasks
   - Reasoning models only when needed

2. **Resource Management:**
   - Preload frequently used models
   - Remove unused models regularly
   - Monitor system resources

3. **Network Optimization:**
   - Use local networks for better latency
   - Consider SSD storage for faster model loading

## Getting Help

**Community Resources:**
- [Ollama GitHub](https://github.com/jmorganca/ollama) - Official repository
- [Ollama Discord](https://discord.gg/ollama) - Community support
- [Open Notebook Discord](https://discord.gg/37XJPXfz2w) - Integration help

**Debugging Resources:**
- Check Ollama logs for error messages
- Test connection with curl commands
- Verify environment variables
- Monitor system resources

This comprehensive guide should help you successfully deploy and optimize Ollama with Open Notebook. Start with the Quick Start section and refer to specific scenarios as needed.