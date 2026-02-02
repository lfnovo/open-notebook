# Local Text-to-Speech Setup

Run text-to-speech locally for free, private podcast generation using OpenAI-compatible TTS servers.

---

## Why Local TTS?

| Benefit | Description |
|---------|-------------|
| **Free** | No per-character costs after setup |
| **Private** | Audio never leaves your machine |
| **Unlimited** | No rate limits or quotas |
| **Offline** | Works without internet |

---

## Quick Start with Speaches

[Speaches](https://github.com/speaches-ai/speaches) is an open-source, OpenAI-compatible TTS server.

### Step 1: Create Docker Compose File

Create a folder and add `docker-compose.yml`:

```yaml
services:
  speaches:
    image: ghcr.io/speaches-ai/speaches:latest-cpu
    container_name: speaches
    ports:
      - "8969:8000"
    volumes:
      - hf-hub-cache:/home/ubuntu/.cache/huggingface/hub
    restart: unless-stopped

volumes:
  hf-hub-cache:
```

### Step 2: Start and Download Model

```bash
# Start Speaches
docker compose up -d

# Wait for startup
sleep 10

# Download voice model (~500MB)
docker compose exec speaches uv tool run speaches-cli model download speaches-ai/Kokoro-82M-v1.0-ONNX
```

### Step 3: Test

```bash
curl "http://localhost:8969/v1/audio/speech" -s \
  -H "Content-Type: application/json" \
  --output test.mp3 \
  --data '{
    "input": "Hello! Local TTS is working.",
    "model": "speaches-ai/Kokoro-82M-v1.0-ONNX",
    "voice": "af_bella"
  }'
```

Play `test.mp3` to verify.

### Step 4: Configure Open Notebook

**Docker deployment:**
```yaml
# In your Open Notebook docker-compose.yml
environment:
  - OPENAI_COMPATIBLE_BASE_URL_TTS=http://host.docker.internal:8969/v1
```

**Local development:**
```bash
export OPENAI_COMPATIBLE_BASE_URL_TTS=http://localhost:8969/v1
```

### Step 5: Add Model in Open Notebook

1. Go to **Settings** → **Models**
2. Click **Add Model** in Text-to-Speech section
3. Configure:
   - **Provider**: `openai_compatible`
   - **Model Name**: `speaches-ai/Kokoro-82M-v1.0-ONNX`
   - **Display Name**: `Local TTS`
4. Click **Save**
5. Set as default if desired

---

## Available Voices

The Kokoro model includes multiple voices:

### Female Voices
| Voice ID | Description |
|----------|-------------|
| `af_bella` | Clear, professional |
| `af_sarah` | Warm, friendly |
| `af_nicole` | Energetic, expressive |

### Male Voices
| Voice ID | Description |
|----------|-------------|
| `am_adam` | Deep, authoritative |
| `am_michael` | Friendly, conversational |

### British Accents
| Voice ID | Description |
|----------|-------------|
| `bf_emma` | British female, professional |
| `bm_george` | British male, formal |

### Test Different Voices

```bash
for voice in af_bella af_sarah am_adam am_michael; do
  curl "http://localhost:8969/v1/audio/speech" -s \
    -H "Content-Type: application/json" \
    --output "test_${voice}.mp3" \
    --data "{
      \"input\": \"Hello, this is the ${voice} voice.\",
      \"model\": \"speaches-ai/Kokoro-82M-v1.0-ONNX\",
      \"voice\": \"${voice}\"
    }"
done
```

---

## GPU Acceleration

For faster generation with NVIDIA GPUs:

```yaml
services:
  speaches:
    image: ghcr.io/speaches-ai/speaches:latest-cuda
    container_name: speaches
    ports:
      - "8969:8000"
    volumes:
      - hf-hub-cache:/home/ubuntu/.cache/huggingface/hub
    restart: unless-stopped
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]

volumes:
  hf-hub-cache:
```

---

## Docker Networking

### Open Notebook in Docker (macOS/Windows)

```bash
OPENAI_COMPATIBLE_BASE_URL_TTS=http://host.docker.internal:8969/v1
```

### Open Notebook in Docker (Linux)

```bash
# Option 1: Docker bridge IP
OPENAI_COMPATIBLE_BASE_URL_TTS=http://172.17.0.1:8969/v1

# Option 2: Host networking
docker run --network host ...
```

### Remote Server

Run Speaches on a different machine:

```bash
# On server, bind to all interfaces
# Then in Open Notebook:
OPENAI_COMPATIBLE_BASE_URL_TTS=http://server-ip:8969/v1
```

---

## Multi-Speaker Podcasts

Configure different voices for each speaker:

```
Speaker 1 (Host):
  Model: speaches-ai/Kokoro-82M-v1.0-ONNX
  Voice: af_bella

Speaker 2 (Guest):
  Model: speaches-ai/Kokoro-82M-v1.0-ONNX
  Voice: am_adam

Speaker 3 (Narrator):
  Model: speaches-ai/Kokoro-82M-v1.0-ONNX
  Voice: bf_emma
```

---

## Troubleshooting

### Service Won't Start

```bash
# Check logs
docker compose logs speaches

# Verify port available
lsof -i :8969

# Restart
docker compose down && docker compose up -d
```

### Connection Refused

```bash
# Test Speaches is running
curl http://localhost:8969/v1/models

# From inside Open Notebook container
docker exec -it open-notebook curl http://host.docker.internal:8969/v1/models
```

### Model Not Found

```bash
# List downloaded models
docker compose exec speaches uv tool run speaches-cli model list

# Download if missing
docker compose exec speaches uv tool run speaches-cli model download speaches-ai/Kokoro-82M-v1.0-ONNX
```

### Poor Audio Quality

- Try different voices
- Adjust speed: `"speed": 0.9` to `1.2`
- Check model downloaded completely
- Allocate more memory

### Slow Generation

| Solution | How |
|----------|-----|
| Use GPU | Switch to `latest-cuda` image |
| More CPU | Allocate more cores in Docker |
| Faster model | Use smaller/quantized models |
| SSD storage | Move Docker volumes to SSD |

---

## Performance Tips

### Recommended Specs

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| CPU | 2 cores | 4+ cores |
| RAM | 2 GB | 4+ GB |
| Storage | 5 GB | 10 GB (for multiple models) |
| GPU | None | NVIDIA (optional) |

### Resource Limits

```yaml
services:
  speaches:
    # ... other config
    mem_limit: 4g
    cpus: 2
```

### Monitor Usage

```bash
docker stats speaches
```

---

## Comparison: Local vs Cloud

| Aspect | Local (Speaches) | Cloud (OpenAI/ElevenLabs) |
|--------|------------------|---------------------------|
| **Cost** | Free | $0.015-0.10/min |
| **Privacy** | Complete | Data sent to provider |
| **Speed** | Depends on hardware | Usually faster |
| **Quality** | Good | Excellent |
| **Setup** | Moderate | Simple API key |
| **Offline** | Yes | No |
| **Voices** | Limited | Many options |

### When to Use Local

- Privacy-sensitive content
- High-volume generation
- Development/testing
- Offline environments
- Cost control

### When to Use Cloud

- Premium quality needs
- Multiple languages
- Time-sensitive projects
- Limited hardware

---

## Other Local TTS Options

Any OpenAI-compatible TTS server works. The key is:

1. Server implements `/v1/audio/speech` endpoint
2. Set `OPENAI_COMPATIBLE_BASE_URL_TTS` to server URL
3. Add model with provider `openai_compatible`

---

## Related

- **[Local STT Setup](local-stt.md)** - Speech-to-text with Speaches
- **[OpenAI-Compatible Providers](openai-compatible.md)** - General compatible provider setup
- **[AI Providers](ai-providers.md)** - All provider configuration
- **[Creating Podcasts](../3-USER-GUIDE/creating-podcasts.md)** - Using TTS for podcasts
