# Local Speech-to-Text Setup

Run speech-to-text locally for free, private audio/video transcription using OpenAI-compatible STT servers.

---

## Why Local STT?

| Benefit | Description |
|---------|-------------|
| **Free** | No per-minute costs after setup |
| **Private** | Audio never leaves your machine |
| **Unlimited** | No rate limits or quotas |
| **Offline** | Works without internet |

---

## Quick Start with Speaches

[Speaches](https://github.com/speaches-ai/speaches) is an open-source, OpenAI-compatible server that supports both TTS and STT. It uses [faster-whisper](https://github.com/SYSTRAN/faster-whisper) for transcription.

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

# Download Whisper model (~500MB for small)
docker compose exec speaches uv tool run speaches-cli model download Systran/faster-whisper-small
```

Models can also be downloaded automatically on first use, but pre-downloading avoids delays.

### Step 3: Test

```bash
# Create a test audio file (or use your own)
# Then transcribe it:
curl "http://localhost:8969/v1/audio/transcriptions" \
  -F "file=@test.mp3" \
  -F "model=Systran/faster-whisper-small"
```

You should see the transcribed text in the response.

### Step 4: Configure Open Notebook

**Docker deployment:**
```yaml
# In your Open Notebook docker-compose.yml
environment:
  - OPENAI_COMPATIBLE_BASE_URL_STT=http://host.docker.internal:8969/v1
```

**Local development:**
```bash
export OPENAI_COMPATIBLE_BASE_URL_STT=http://localhost:8969/v1
```

### Step 5: Add Model in Open Notebook

1. Go to **Settings** → **Models**
2. Click **Add Model** in Speech-to-Text section
3. Configure:
   - **Provider**: `openai_compatible`
   - **Model Name**: `Systran/faster-whisper-small`
   - **Display Name**: `Local Whisper`
4. Click **Save**
5. Set as default if desired

---

## Available Models

Speaches supports various Whisper model sizes. Larger models are more accurate but slower:

| Model | Size | Speed | Accuracy | VRAM (GPU) |
|-------|------|-------|----------|------------|
| `Systran/faster-whisper-tiny` | ~75 MB | Fastest | Basic | ~1 GB |
| `Systran/faster-whisper-base` | ~150 MB | Fast | Good | ~1 GB |
| `Systran/faster-whisper-small` | ~500 MB | Medium | Better | ~2 GB |
| `Systran/faster-whisper-medium` | ~1.5 GB | Slow | Great | ~5 GB |
| `Systran/faster-whisper-large-v3` | ~3 GB | Slowest | Best | ~10 GB |
| `Systran/faster-distil-whisper-small.en` | ~400 MB | Fast | Good (English only) | ~2 GB |

### List Available Models

```bash
docker compose exec speaches uv tool run speaches-cli registry ls --task automatic-speech-recognition
```

### Recommended Models

- **For speed**: `Systran/faster-whisper-tiny` or `Systran/faster-whisper-base`
- **For balance**: `Systran/faster-whisper-small` (recommended)
- **For accuracy**: `Systran/faster-whisper-large-v3`

---

## GPU Acceleration

For faster transcription with NVIDIA GPUs:

```yaml
services:
  speaches:
    image: ghcr.io/speaches-ai/speaches:latest-cuda
    container_name: speaches
    ports:
      - "8969:8000"
    volumes:
      - hf-hub-cache:/home/ubuntu/.cache/huggingface/hub
    environment:
      - WHISPER__TTL=-1  # Keep model in VRAM (recommended if you have enough memory)
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

### Keep Model in Memory

By default, Speaches unloads models after some time. To keep the Whisper model loaded for instant transcription:

```yaml
environment:
  - WHISPER__TTL=-1  # Never unload
```

This is recommended if you have enough RAM/VRAM, as loading the model can take a few seconds.

---

## Docker Networking

### Open Notebook in Docker (macOS/Windows)

```bash
OPENAI_COMPATIBLE_BASE_URL_STT=http://host.docker.internal:8969/v1
```

### Open Notebook in Docker (Linux)

```bash
# Option 1: Docker bridge IP
OPENAI_COMPATIBLE_BASE_URL_STT=http://172.17.0.1:8969/v1

# Option 2: Host networking
docker run --network host ...
```

### Remote Server

Run Speaches on a different machine:

```bash
# On server, bind to all interfaces
# Then in Open Notebook:
OPENAI_COMPATIBLE_BASE_URL_STT=http://server-ip:8969/v1
```

---

## Language Support

Whisper supports 99+ languages. Specify the language for better accuracy:

```bash
curl "http://localhost:8969/v1/audio/transcriptions" \
  -F "file=@audio.mp3" \
  -F "model=Systran/faster-whisper-small" \
  -F "language=ru"
```

Common language codes:
- `en` - English
- `ru` - Russian
- `es` - Spanish
- `fr` - French
- `de` - German
- `zh` - Chinese
- `ja` - Japanese

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

### Model Download Fails

Models are downloaded automatically on first use. If download fails:

```bash
# Check available disk space
df -h

# Check Docker logs for errors
docker compose logs speaches

# Restart and try again
docker compose restart speaches
```

### Poor Transcription Quality

- Use a larger model (`faster-whisper-medium` or `large-v3`)
- Specify the correct language
- Ensure audio quality is good (clear speech, minimal background noise)
- Try different audio formats (WAV often works better than MP3)

### Slow Transcription

| Solution | How |
|----------|-----|
| Use GPU | Switch to `latest-cuda` image |
| Smaller model | Use `faster-whisper-tiny` or `base` |
| More CPU | Allocate more cores in Docker |
| SSD storage | Move Docker volumes to SSD |

---

## Performance Tips

### Recommended Specs

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| CPU | 2 cores | 4+ cores |
| RAM | 2 GB | 8+ GB |
| Storage | 5 GB | 10 GB (for multiple models) |
| GPU | None | NVIDIA (optional, much faster) |

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

| Aspect | Local (Speaches) | Cloud (OpenAI Whisper) |
|--------|------------------|------------------------|
| **Cost** | Free | $0.006/min |
| **Privacy** | Complete | Data sent to provider |
| **Speed** | Depends on hardware | Usually faster |
| **Quality** | Excellent (same Whisper) | Excellent |
| **Setup** | Moderate | Simple API key |
| **Offline** | Yes | No |
| **Languages** | 99+ | 99+ |

### When to Use Local

- Privacy-sensitive content
- High-volume transcription
- Development/testing
- Offline environments
- Cost control

### When to Use Cloud

- Limited hardware
- Time-sensitive projects
- No GPU available
- Simple setup preferred

---

## Using Both TTS and STT

Speaches supports both TTS and STT in one server. Configure both:

```bash
# Same server for both
OPENAI_COMPATIBLE_BASE_URL_TTS=http://localhost:8969/v1
OPENAI_COMPATIBLE_BASE_URL_STT=http://localhost:8969/v1
```

See **[Local TTS Setup](local-tts.md)** for TTS configuration.

---

## Other Local STT Options

Any OpenAI-compatible STT server works:

| Server | Description |
|--------|-------------|
| [Speaches](https://github.com/speaches-ai/speaches) | TTS + STT in one (recommended) |
| [faster-whisper-server](https://github.com/fedirz/faster-whisper-server) | Lightweight STT only |
| [whisper.cpp](https://github.com/ggerganov/whisper.cpp) | C++ implementation with server mode |
| [LocalAI](https://github.com/mudler/LocalAI) | Multi-model local AI server |

The key requirements:

1. Server implements `/v1/audio/transcriptions` endpoint
2. Set `OPENAI_COMPATIBLE_BASE_URL_STT` to server URL
3. Add model with provider `openai_compatible`

---

## Related

- **[Local TTS Setup](local-tts.md)** - Text-to-speech with Speaches
- **[OpenAI-Compatible Providers](openai-compatible.md)** - General compatible provider setup
- **[AI Providers](ai-providers.md)** - All provider configuration