# OpenAI-Compatible Providers

Use any server that implements the OpenAI API format with Open Notebook. This includes LM Studio, Text Generation WebUI, vLLM, and many others.

---

## What is OpenAI-Compatible?

Many AI tools implement the same API format as OpenAI:

```
POST /v1/chat/completions
POST /v1/embeddings
POST /v1/audio/speech
```

Open Notebook can connect to any server using this format.

---

## Common Compatible Servers

| Server | Use Case | URL |
|--------|----------|-----|
| **LM Studio** | Desktop GUI for local models | https://lmstudio.ai |
| **Text Generation WebUI** | Full-featured local inference | https://github.com/oobabooga/text-generation-webui |
| **vLLM** | High-performance serving | https://github.com/vllm-project/vllm |
| **Ollama** | Simple local models | (Use native Ollama provider instead) |
| **LocalAI** | Local AI inference | https://github.com/mudler/LocalAI |
| **llama.cpp server** | Lightweight inference | https://github.com/ggerganov/llama.cpp |

---

## Quick Setup: LM Studio

### Step 1: Install and Start LM Studio

1. Download from https://lmstudio.ai
2. Install and launch
3. Download a model (e.g., Llama 3)
4. Start the local server (default: port 1234)

### Step 2: Configure Environment

```bash
# For language models
export OPENAI_COMPATIBLE_BASE_URL=http://localhost:1234/v1
export OPENAI_COMPATIBLE_API_KEY=not-needed  # LM Studio doesn't require key
```

### Step 3: Add Model in Open Notebook

1. Go to **Settings** → **Models**
2. Click **Add Model**
3. Configure:
   - **Provider**: `openai_compatible`
   - **Model Name**: Your model name from LM Studio
   - **Display Name**: `LM Studio - Llama 3`
4. Click **Save**

---

## Environment Variables

### Language Models (Chat)

```bash
OPENAI_COMPATIBLE_BASE_URL=http://localhost:1234/v1
OPENAI_COMPATIBLE_API_KEY=optional-api-key
```

### Embeddings

```bash
OPENAI_COMPATIBLE_BASE_URL_EMBEDDING=http://localhost:1234/v1
OPENAI_COMPATIBLE_BASE_URL_EMBEDDING=optional-api-key
```

### Text-to-Speech

```bash
OPENAI_COMPATIBLE_BASE_URL_TTS=http://localhost:8969/v1
OPENAI_COMPATIBLE_API_KEY_TTS=optional-api-key
```

### Speech-to-Text

```bash
OPENAI_COMPATIBLE_BASE_URL_STT=http://localhost:9000/v1
OPENAI_COMPATIBLE_API_KEY_STT=optional-api-key
```

---

## Docker Networking

When Open Notebook runs in Docker and your compatible server runs on the host:

### macOS / Windows

```bash
OPENAI_COMPATIBLE_BASE_URL=http://host.docker.internal:1234/v1
```

### Linux

```bash
# Option 1: Docker bridge IP
OPENAI_COMPATIBLE_BASE_URL=http://172.17.0.1:1234/v1

# Option 2: Host networking mode
docker run --network host ...
```

### Same Docker Network

```yaml
# docker-compose.yml
services:
  open-notebook:
    # ...
    environment:
      - OPENAI_COMPATIBLE_BASE_URL=http://lm-studio:1234/v1

  lm-studio:
    # your LM Studio container
    ports:
      - "1234:1234"
```

---

## Text Generation WebUI Setup

### Start with API Enabled

```bash
python server.py --api --listen
```

### Configure Open Notebook

```bash
OPENAI_COMPATIBLE_BASE_URL=http://localhost:5000/v1
```

### Docker Compose Example

```yaml
services:
  text-gen:
    image: atinoda/text-generation-webui:default
    ports:
      - "5000:5000"
      - "7860:7860"
    volumes:
      - ./models:/app/models
    command: --api --listen

  open-notebook:
    image: lfnovo/open_notebook:v1-latest-single
    pull_policy: always
    environment:
      - OPENAI_COMPATIBLE_BASE_URL=http://text-gen:5000/v1
    depends_on:
      - text-gen
```

---

## vLLM Setup

### Start vLLM Server

```bash
python -m vllm.entrypoints.openai.api_server \
  --model meta-llama/Llama-3.1-8B-Instruct \
  --port 8000
```

### Configure Open Notebook

```bash
OPENAI_COMPATIBLE_BASE_URL=http://localhost:8000/v1
```

### Docker Compose with GPU

```yaml
services:
  vllm:
    image: vllm/vllm-openai:latest
    command: --model meta-llama/Llama-3.1-8B-Instruct
    ports:
      - "8000:8000"
    volumes:
      - ~/.cache/huggingface:/root/.cache/huggingface
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]

  open-notebook:
    image: lfnovo/open_notebook:v1-latest-single
    pull_policy: always
    environment:
      - OPENAI_COMPATIBLE_BASE_URL=http://vllm:8000/v1
    depends_on:
      - vllm
```

---

## Adding Models in Open Notebook

### Via Settings UI

1. Go to **Settings** → **Models**
2. Click **Add Model** in appropriate section
3. Select **Provider**: `openai_compatible`
4. Enter **Model Name**: exactly as the server expects
5. Enter **Display Name**: your preferred name
6. Click **Save**

### Model Name Format

The model name must match what your server expects:

| Server | Model Name Format |
|--------|-------------------|
| LM Studio | As shown in LM Studio UI |
| vLLM | HuggingFace model path |
| Text Gen WebUI | As loaded in UI |
| llama.cpp | Model file name |

---

## Testing Connection

### Test API Endpoint

```bash
# Test chat completions
curl http://localhost:1234/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "your-model-name",
    "messages": [{"role": "user", "content": "Hello"}]
  }'
```

### Test from Inside Docker

```bash
docker exec -it open-notebook curl http://host.docker.internal:1234/v1/models
```

---

## Troubleshooting

### Connection Refused

```
Problem: Cannot connect to server

Solutions:
1. Verify server is running
2. Check port is correct
3. Test with curl directly
4. Check Docker networking (use host.docker.internal)
5. Verify firewall allows connection
```

### Model Not Found

```
Problem: Server returns "model not found"

Solutions:
1. Check model is loaded in server
2. Verify exact model name spelling
3. List available models: curl http://localhost:1234/v1/models
4. Update model name in Open Notebook
```

### Slow Responses

```
Problem: Requests take very long

Solutions:
1. Check server resources (RAM, GPU)
2. Use smaller/quantized model
3. Reduce context length
4. Enable GPU acceleration if available
```

### Authentication Errors

```
Problem: 401 or authentication failed

Solutions:
1. Check if server requires API key
2. Set OPENAI_COMPATIBLE_API_KEY
3. Some servers need any non-empty key
```

### Timeout Errors

```
Problem: Request times out

Solutions:
1. Model may be loading (first request slow)
2. Increase timeout settings
3. Check server logs for errors
4. Reduce request size
```

---

## Multiple Compatible Endpoints

You can use different compatible servers for different purposes:

```bash
# Chat model from LM Studio
OPENAI_COMPATIBLE_BASE_URL=http://localhost:1234/v1

# Embeddings from different server
OPENAI_COMPATIBLE_BASE_URL_EMBEDDING=http://localhost:8080/v1

# TTS from Speaches
OPENAI_COMPATIBLE_BASE_URL_TTS=http://localhost:8969/v1
```

Add each as a separate model in Open Notebook settings.

---

## Performance Tips

### Model Selection

| Model Size | RAM Needed | Speed |
|------------|------------|-------|
| 7B | 8GB | Fast |
| 13B | 16GB | Medium |
| 70B | 64GB+ | Slow |

### Quantization

Use quantized models (Q4, Q5) for faster inference with less RAM:

```
llama-3-8b-q4_k_m.gguf  → ~4GB RAM, fast
llama-3-8b-f16.gguf     → ~16GB RAM, slower
```

### GPU Acceleration

Enable GPU in your server for much faster inference:
- LM Studio: Settings → GPU layers
- vLLM: Automatic with CUDA
- llama.cpp: `--n-gpu-layers 35`

---

## Comparison: Native vs Compatible

| Aspect | Native Provider | OpenAI Compatible |
|--------|-----------------|-------------------|
| **Setup** | API key only | Server + configuration |
| **Models** | Provider's models | Any compatible model |
| **Cost** | Pay per token | Free (local) |
| **Speed** | Usually fast | Depends on hardware |
| **Features** | Full support | Basic features |

Use OpenAI-compatible when:
- Running local models
- Using custom/fine-tuned models
- Privacy requirements
- Cost control

---

## Related

- **[Local TTS Setup](local-tts.md)** - Text-to-speech with Speaches
- **[Local STT Setup](local-stt.md)** - Speech-to-text with Speaches
- **[AI Providers](ai-providers.md)** - All provider options
- **[Ollama Setup](ollama.md)** - Native Ollama integration
