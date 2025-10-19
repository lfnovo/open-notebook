# OpenAI-Compatible Providers Setup Guide

Open Notebook supports OpenAI-compatible API endpoints across all AI modalities (language models, embeddings, speech-to-text, and text-to-speech), giving you the flexibility to use popular tools like LM Studio, Text Generation WebUI, vLLM, and custom inference servers.

## Why Choose OpenAI-Compatible Providers?

- **🆓 Cost Flexibility**: Use free local inference or choose cost-effective cloud providers
- **🔒 Privacy Control**: Run models locally or choose privacy-focused hosted services
- **🎯 Model Selection**: Access to thousands of open-source models
- **⚡ Performance Tuning**: Optimize inference for your specific hardware
- **🔧 Full Control**: Deploy on your infrastructure with your configurations
- **🌐 Universal Standard**: Works with any service that implements the OpenAI API specification

## Quick Start

### Basic Setup (All Modalities)

**For LM Studio** (simplest):
```bash
# Start LM Studio and enable server mode on port 1234
export OPENAI_COMPATIBLE_BASE_URL=http://localhost:1234/v1

# Most LM Studio endpoints don't require an API key
# export OPENAI_COMPATIBLE_API_KEY=not_needed
```

**For Text Generation WebUI**:
```bash
# Start with --api flag
# python server.py --api --listen

export OPENAI_COMPATIBLE_BASE_URL=http://localhost:5000/v1
```

**For vLLM**:
```bash
# Start vLLM server
# vllm serve MODEL_NAME --port 8000

export OPENAI_COMPATIBLE_BASE_URL=http://localhost:8000/v1
```

### Advanced Setup (Mode-Specific Endpoints)

Use different endpoints for different capabilities:

```bash
# Language models on LM Studio
export OPENAI_COMPATIBLE_BASE_URL_LLM=http://localhost:1234/v1

# Embeddings on a dedicated embedding server
export OPENAI_COMPATIBLE_BASE_URL_EMBEDDING=http://localhost:8080/v1

# Speech services on a different server
export OPENAI_COMPATIBLE_BASE_URL_STT=http://localhost:9000/v1
export OPENAI_COMPATIBLE_BASE_URL_TTS=http://localhost:8969/v1
```

> **🎙️ Want free, local text-to-speech?** Check our [Local TTS Setup Guide](local_tts.md) for completely private, zero-cost podcast generation!

## Environment Variable Reference

### Generic Configuration

Use these when you want the same endpoint for all modalities:

| Variable | Purpose | Required |
|----------|---------|----------|
| `OPENAI_COMPATIBLE_BASE_URL` | Base URL for all AI services | Yes (unless using mode-specific) |
| `OPENAI_COMPATIBLE_API_KEY` | API key if endpoint requires auth | Optional |

**Example:**
```bash
export OPENAI_COMPATIBLE_BASE_URL=http://localhost:1234/v1
export OPENAI_COMPATIBLE_API_KEY=your_key_here  # If needed
```

### Mode-Specific Configuration

Use these when you want different endpoints for different capabilities:

| Variable | Purpose | Modality |
|----------|---------|----------|
| `OPENAI_COMPATIBLE_BASE_URL_LLM` | Language model endpoint | Language models |
| `OPENAI_COMPATIBLE_API_KEY_LLM` | API key for LLM endpoint | Language models |
| `OPENAI_COMPATIBLE_BASE_URL_EMBEDDING` | Embedding model endpoint | Embeddings |
| `OPENAI_COMPATIBLE_API_KEY_EMBEDDING` | API key for embedding endpoint | Embeddings |
| `OPENAI_COMPATIBLE_BASE_URL_STT` | Speech-to-text endpoint | Speech-to-Text |
| `OPENAI_COMPATIBLE_API_KEY_STT` | API key for STT endpoint | Speech-to-Text |
| `OPENAI_COMPATIBLE_BASE_URL_TTS` | Text-to-speech endpoint | Text-to-Speech |
| `OPENAI_COMPATIBLE_API_KEY_TTS` | API key for TTS endpoint | Text-to-Speech |

**Precedence**: Mode-specific variables override the generic `OPENAI_COMPATIBLE_BASE_URL`

**Example:**
```bash
# LLM on LM Studio
export OPENAI_COMPATIBLE_BASE_URL_LLM=http://localhost:1234/v1

# Embeddings on dedicated server
export OPENAI_COMPATIBLE_BASE_URL_EMBEDDING=http://localhost:8080/v1
export OPENAI_COMPATIBLE_API_KEY_EMBEDDING=secret_key_here
```

## Common Use Cases

### LM Studio

**What is LM Studio?**
LM Studio is a desktop application for running large language models locally with a user-friendly interface.

**Setup Steps:**
1. **Download and install** LM Studio from [lmstudio.ai](https://lmstudio.ai/)
2. **Download a model** (e.g., Llama 3, Qwen, Mistral)
3. **Start the local server**:
   - Go to the "Local Server" tab
   - Click "Start Server"
   - Note the port (default: 1234)

4. **Configure Open Notebook**:
```bash
export OPENAI_COMPATIBLE_BASE_URL=http://localhost:1234/v1
```

**What works:**
- ✅ Language models (chat, completions)
- ✅ Embeddings (with embedding models)
- ❌ Speech-to-text (not supported)
- ❌ Text-to-speech (not supported)

**Tips:**
- LM Studio doesn't require an API key
- Choose quantized models (Q4, Q5) for better performance
- Monitor RAM usage - larger models need more memory

---

### Text Generation WebUI (Oobabooga)

**What is Text Generation WebUI?**
A powerful Gradio-based web interface for running Large Language Models.

**Setup Steps:**
1. **Install** following [official instructions](https://github.com/oobabooga/text-generation-webui)
2. **Download a model** using the UI or manually
3. **Start with API mode**:
```bash
python server.py --api --listen
```

4. **Configure Open Notebook**:
```bash
export OPENAI_COMPATIBLE_BASE_URL=http://localhost:5000/v1
```

**What works:**
- ✅ Language models (excellent support)
- ✅ Embeddings (with compatible models)
- ❌ Speech services (not supported)

**Tips:**
- Use `--listen` to accept connections from Docker
- Supports more model formats than LM Studio
- Great for fine-tuned models

---

### vLLM

**What is vLLM?**
High-performance inference server optimized for serving large language models at scale.

**Setup Steps:**
1. **Install vLLM**:
```bash
pip install vllm
```

2. **Start the server**:
```bash
vllm serve meta-llama/Llama-3-8B-Instruct --port 8000
```

3. **Configure Open Notebook**:
```bash
export OPENAI_COMPATIBLE_BASE_URL=http://localhost:8000/v1
```

**What works:**
- ✅ Language models (optimized inference)
- ✅ Embeddings (with embedding models)
- ❌ Speech services (not supported)

**Tips:**
- Best performance for production deployments
- Supports tensor parallelism for large models
- Excellent for high-throughput scenarios

---

### Custom OpenAI-Compatible Services

Many services implement the OpenAI API specification:

**Examples:**
- **Together AI**: Cloud-hosted models
- **Anyscale Endpoints**: Ray-based inference
- **Replicate**: Cloud model hosting
- **LocalAI**: Self-hosted alternative to OpenAI
- **FastChat**: Multi-model serving

**Configuration:**
```bash
# Generic setup
export OPENAI_COMPATIBLE_BASE_URL=https://api.your-service.com/v1
export OPENAI_COMPATIBLE_API_KEY=your_api_key_here
```

## Configuration Scenarios

### Scenario 1: Single Local Endpoint (Simplest)

**Use Case**: Running LM Studio for language models only

```bash
export OPENAI_COMPATIBLE_BASE_URL=http://localhost:1234/v1
```

**Result**:
- ✅ Language models available
- ✅ Embeddings available (if model supports)
- ✅ Speech services available (if endpoint supports)
- All use the same endpoint

---

### Scenario 2: Separate Endpoints per Modality

**Use Case**: Language models on LM Studio, embeddings on dedicated server

```bash
# Language models on LM Studio
export OPENAI_COMPATIBLE_BASE_URL_LLM=http://localhost:1234/v1

# Embeddings on specialized server
export OPENAI_COMPATIBLE_BASE_URL_EMBEDDING=http://localhost:8080/v1
export OPENAI_COMPATIBLE_API_KEY_EMBEDDING=embedding_key_here
```

**Result**:
- ✅ Language models use LM Studio (port 1234)
- ✅ Embeddings use specialized server (port 8080)
- ❌ Speech services not available (not configured)

---

### Scenario 3: Mixed Local and Cloud

**Use Case**: Local models for privacy, cloud for specialized tasks

```bash
# Local LLM (privacy-sensitive work)
export OPENAI_COMPATIBLE_BASE_URL_LLM=http://localhost:1234/v1

# Cloud embeddings (better quality)
export OPENAI_COMPATIBLE_BASE_URL_EMBEDDING=https://api.cloud-provider.com/v1
export OPENAI_COMPATIBLE_API_KEY_EMBEDDING=cloud_key_here

# Cloud speech services
export OPENAI_COMPATIBLE_BASE_URL_TTS=https://api.cloud-provider.com/v1
export OPENAI_COMPATIBLE_API_KEY_TTS=cloud_key_here
```

**Result**:
- ✅ Sensitive chat stays local
- ✅ High-quality embeddings from cloud
- ✅ Professional TTS from cloud
- 🔒 Privacy for conversations, cloud for non-sensitive features

---

### Scenario 4: Docker Deployment

**Use Case**: Open Notebook in Docker, LM Studio on host machine

**On macOS/Windows**:
```bash
export OPENAI_COMPATIBLE_BASE_URL=http://host.docker.internal:1234/v1
```

**On Linux**:
```bash
# Use host networking or find host IP
export OPENAI_COMPATIBLE_BASE_URL=http://172.17.0.1:1234/v1
# or use --network host in docker run
```

**Important**:
- LM Studio must be set to listen on `0.0.0.0`, not just `localhost`
- In LM Studio settings, enable "Allow network connections"

## Network Configuration

### Docker Networking

**Problem**: Docker containers can't reach `localhost` on the host

**Solutions:**

**Option 1: Use `host.docker.internal` (Mac/Windows)**
```bash
export OPENAI_COMPATIBLE_BASE_URL=http://host.docker.internal:1234/v1
```

**Option 2: Use host IP address (Linux)**
```bash
# Find host IP
ip addr show docker0 | grep inet

# Use in environment
export OPENAI_COMPATIBLE_BASE_URL=http://172.17.0.1:1234/v1
```

**Option 3: Host networking (Linux only)**
```bash
docker run --network host \
  -v ./notebook_data:/app/data \
  -e OPENAI_COMPATIBLE_BASE_URL=http://localhost:1234/v1 \
  lfnovo/open_notebook:v1-latest-single
```

### Remote Servers

**Use Case**: OpenAI-compatible service on a different machine

```bash
# Replace with your server's IP or hostname
export OPENAI_COMPATIBLE_BASE_URL=http://192.168.1.100:1234/v1
```

**Security Notes:**
- ⚠️ Only use on trusted networks
- Consider using HTTPS for production
- Implement API key authentication if possible
- Use firewall rules to restrict access

### Port Conflicts

**Problem**: Default port (1234) is already in use

**Solution**: Change the port in your inference server

**LM Studio:**
- Settings → Local Server → Port → Change to different port

**Then update environment:**
```bash
export OPENAI_COMPATIBLE_BASE_URL=http://localhost:8888/v1
```

## Troubleshooting

### Connection Refused

**Symptom**: "Connection refused" or "Could not connect to endpoint"

**Solutions:**
1. **Verify server is running**:
   ```bash
   curl http://localhost:1234/v1/models
   ```

2. **Check firewall settings**: Ensure the port is not blocked

3. **For Docker**: Use `host.docker.internal` instead of `localhost`

4. **Check server binding**: Server must listen on `0.0.0.0`, not just `127.0.0.1`

---

### Models Not Found

**Symptom**: "Model not found" or "No models available"

**Solutions:**
1. **Verify model is loaded** in your inference server
2. **Check model name** matches what Open Notebook expects
3. **For LM Studio**: Ensure model is loaded in the local server tab
4. **Test endpoint**:
   ```bash
   curl http://localhost:1234/v1/models
   ```

---

### Slow Performance

**Symptom**: Responses take a long time

**Solutions:**
1. **Use quantized models** (Q4, Q5 instead of full precision)
2. **Check RAM usage**: Model might be swapping to disk
3. **Reduce context length**: Smaller context = faster inference
4. **Enable GPU acceleration**: If available
5. **For vLLM**: Enable tensor parallelism for large models

---

### Authentication Errors

**Symptom**: "Unauthorized" or "Invalid API key"

**Solutions:**
1. **Set API key** if your endpoint requires it:
   ```bash
   export OPENAI_COMPATIBLE_API_KEY=your_key_here
   ```

2. **Check key validity**: Test with curl:
   ```bash
   curl -H "Authorization: Bearer YOUR_KEY" \
     http://localhost:1234/v1/models
   ```

3. **For mode-specific**: Use the correct key variable:
   ```bash
   export OPENAI_COMPATIBLE_API_KEY_LLM=llm_key
   export OPENAI_COMPATIBLE_API_KEY_EMBEDDING=embedding_key
   ```

---

### Docker Can't Reach Host

**Symptom**: Connection works locally but not from Docker

**Solutions:**
1. **Use `host.docker.internal`** (Mac/Windows):
   ```bash
   export OPENAI_COMPATIBLE_BASE_URL=http://host.docker.internal:1234/v1
   ```

2. **On Linux**: Use host IP or `--network host`

3. **Check server listening**: Must listen on `0.0.0.0:1234`, not `127.0.0.1:1234`

4. **Test from inside container**:
   ```bash
   docker exec -it open-notebook curl http://host.docker.internal:1234/v1/models
   ```

---

### Embeddings Not Working

**Symptom**: Search or embeddings fail

**Solutions:**
1. **Verify embedding model is loaded**: Many inference servers need explicit embedding model setup
2. **Use dedicated embedding endpoint**: If available
3. **Check model compatibility**: Not all models support embeddings
4. **For LM Studio**: Load an embedding model separately

---

### Mixed Results (Some Modes Work, Others Don't)

**Symptom**: Language models work, but embeddings or speech don't

**Solution**: Use mode-specific configuration:
```bash
# What works
export OPENAI_COMPATIBLE_BASE_URL_LLM=http://localhost:1234/v1

# For embeddings, use a different provider
export OPENAI_API_KEY=your_openai_key  # Fallback to OpenAI for embeddings
```

## Best Practices

### Security

1. **API Keys**:
   - Use environment variables, never hardcode
   - Rotate keys regularly for cloud services
   - Use different keys for different services

2. **Network**:
   - Only expose on trusted networks
   - Use HTTPS in production
   - Implement firewall rules

3. **Data Privacy**:
   - Use local models for sensitive data
   - Check service privacy policies
   - Understand data retention policies

### Performance

1. **Model Selection**:
   - Quantized models (Q4, Q5) for better speed/memory trade-off
   - Smaller models for simple tasks
   - Larger models only when needed

2. **Resource Management**:
   - Monitor RAM and GPU usage
   - Use appropriate batch sizes
   - Consider model caching strategies

3. **Network**:
   - Use local endpoints when possible for lower latency
   - For cloud: Choose geographically close servers

### Reliability

1. **Fallback Strategy**:
   ```bash
   # Primary: Local LLM
   export OPENAI_COMPATIBLE_BASE_URL_LLM=http://localhost:1234/v1

   # Fallback: Use OpenAI if local is unavailable
   export OPENAI_API_KEY=your_backup_key
   ```

2. **Health Checks**:
   - Periodically test endpoints
   - Monitor server status
   - Set up alerts for downtime

3. **Testing**:
   - Test configuration before production
   - Validate all required modalities work
   - Check error handling

## Related Guides

**OpenAI-Compatible Setups:**
- **[Local TTS Setup](local_tts.md)** - Free, private text-to-speech for podcasts
- **[Ollama Setup](ollama.md)** - Local language models and embeddings
- **[AI Models Guide](ai-models.md)** - Complete model configuration overview

## Getting Help

**Community Resources:**
- [Open Notebook Discord](https://discord.gg/37XJPXfz2w) - Get help with Open Notebook integration
- [LM Studio Discord](https://discord.gg/lmstudio) - LM Studio-specific support
- [Text Generation WebUI GitHub](https://github.com/oobabooga/text-generation-webui) - Issues and discussions

**Debugging Steps:**
1. **Test endpoint directly** with curl before configuring Open Notebook
2. **Check Open Notebook logs** for detailed error messages
3. **Verify environment variables** are set correctly
4. **Test with simple requests** first (list models, simple completion)

**Common curl tests:**
```bash
# List models
curl http://localhost:1234/v1/models

# Test completion
curl http://localhost:1234/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "your-model",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'

# Test embeddings
curl http://localhost:8080/v1/embeddings \
  -H "Content-Type: application/json" \
  -d '{
    "model": "embedding-model",
    "input": "Test text"
  }'
```

This guide should help you successfully configure OpenAI-compatible providers with Open Notebook. For general AI model configuration, see the [AI Models Guide](ai-models.md).