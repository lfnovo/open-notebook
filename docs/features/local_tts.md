# Local Text-to-Speech Setup

Learn how to run text-to-speech models completely locally using OpenAI-compatible TTS servers, giving you full privacy control and zero ongoing costs for podcast and audio generation.

This guide uses **Speaches** as an example implementation, but the principles apply to any OpenAI-compatible TTS server.

## Why Local Text-to-Speech?

Running text-to-speech locally offers significant advantages:

- **🔒 Complete Privacy**: Your content never leaves your machine
- **💰 Zero Ongoing Costs**: No per-character or per-minute charges
- **⚡ No Rate Limits**: Generate unlimited audio without restrictions
- **🌐 Offline Capability**: Works without internet connection
- **🎯 Full Control**: Choose and customize your voice models
- **📈 Predictable Costs**: One-time setup, no surprises

## Available Local TTS Solutions

Open Notebook supports any OpenAI-compatible text-to-speech server. This guide uses **Speaches** as an example because it's:

- Open-source and actively maintained
- Easy to set up with Docker
- Compatible with OpenAI's TTS API specification
- Supports multiple high-quality voice models

### About Speaches

[Speaches](https://github.com/speaches-ai/speaches) is an open-source, OpenAI-compatible text-to-speech server that runs locally on your machine. It provides:

- **OpenAI API Compatibility**: Works seamlessly with Open Notebook's OpenAI-compatible provider
- **High-Quality Voices**: Support for multiple neural TTS models
- **Easy Model Management**: Simple CLI for downloading and managing voice models
- **Docker Support**: Run in containers for easy deployment
- **Multiple Voice Options**: Various voices and languages available
- **Customizable Speed**: Adjust speech rate to your preference

> **Note**: If you're using a different OpenAI-compatible TTS server, the configuration steps will be similar - just adjust the endpoints and model names accordingly.

## Quick Start with Speaches

This section demonstrates setup using Speaches as an example. If you're using a different local TTS solution, adapt the steps accordingly.

### Prerequisites

- **Docker** installed on your system
- At least **2GB RAM** available
- **5GB disk space** for models

### Basic Setup

The fastest way to get started is using our example setup:

**1. Create a project directory:**
```bash
mkdir speaches-setup
cd speaches-setup
```

**2. Create a `docker-compose.yml` file:**
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

**3. Start the Speaches server:**
```bash
docker compose up -d
```

**4. Download a TTS model:**
```bash
# Wait a few seconds for the container to start
sleep 10

# Download the recommended Kokoro model
docker compose exec speaches uv tool run speaches-cli model download speaches-ai/Kokoro-82M-v1.0-ONNX
```

**5. Test the setup:**
```bash
curl "http://localhost:8969/v1/audio/speech" -s -H "Content-Type: application/json" \
  --output test.mp3 \
  --data '{
    "input": "Hello! This is a test of local text to speech.",
    "model": "speaches-ai/Kokoro-82M-v1.0-ONNX",
    "voice": "af_bella",
    "speed": 1.0
  }'
```

If successful, you'll have a `test.mp3` file with the generated speech!

### Configure Open Notebook

Now that Speaches is running, configure Open Notebook to use it:

**1. Set the environment variable:**

For Docker deployments:
```bash
docker run -d \
  --name open-notebook \
  -p 8502:8502 -p 5055:5055 \
  -v ./notebook_data:/app/data \
  -v ./surreal_data:/mydata \
  -e OPENAI_COMPATIBLE_BASE_URL_TTS=http://host.docker.internal:8969/v1 \
  lfnovo/open_notebook:v1-latest-single
```

For local development:
```bash
export OPENAI_COMPATIBLE_BASE_URL_TTS=http://localhost:8969/v1
```

**2. Add the model in Open Notebook:**

1. Go to **Settings** → **Models** page
2. Click **Add Model** in the Text-to-Speech section
3. Configure the model:
   - **Provider**: `openai_compatible`
   - **Model Name**: `speaches-ai/Kokoro-82M-v1.0-ONNX`
   - **Display Name**: `Kokoro Local TTS` (or your preference)
4. Click **Save**

**3. Set as default (optional):**
- In Settings, set this model as your default Text-to-Speech model
- Now all podcast generation will use your local TTS

## Available Voice Models

Speaches supports various TTS models from Hugging Face. Here are some recommended options:

### Kokoro (Recommended)
- **Model ID**: `speaches-ai/Kokoro-82M-v1.0-ONNX`
- **Size**: ~500MB
- **Quality**: High
- **Speed**: Fast
- **Languages**: English
- **Voices**: `af_bella`, `af_sarah`, `am_adam`, `am_michael`, and more

### Other Models
You can use any compatible ONNX TTS model from Hugging Face. Check the [Speaches documentation](https://github.com/speaches-ai/speaches) for a complete list.

## Available Voices

The Kokoro model includes multiple voices with different characteristics:

**Female Voices:**
- `af_bella` - Clear, professional
- `af_sarah` - Warm, friendly
- `af_nicole` - Energetic, expressive

**Male Voices:**
- `am_adam` - Deep, authoritative
- `am_michael` - Friendly, conversational
- `bf_emma` - British accent, professional
- `bm_george` - British accent, formal

**Testing Voices:**
```bash
# Try different voices to find your favorite
for voice in af_bella af_sarah am_adam am_michael; do
  curl "http://localhost:8969/v1/audio/speech" -s \
    -H "Content-Type: application/json" \
    --output "test_${voice}.mp3" \
    --data "{
      \"input\": \"Hello! This is a test of the ${voice} voice.\",
      \"model\": \"speaches-ai/Kokoro-82M-v1.0-ONNX\",
      \"voice\": \"${voice}\"
    }"
done
```

## Advanced Configuration

### GPU Acceleration

For faster processing with NVIDIA GPUs:

```yaml
services:
  speaches:
    image: ghcr.io/speaches-ai/speaches:latest-cuda  # GPU-enabled image
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

### Custom Port

If port 8969 is already in use, change it in docker-compose.yml:

```yaml
ports:
  - "9000:8000"  # Use port 9000 instead
```

Then update your environment variable:
```bash
export OPENAI_COMPATIBLE_BASE_URL_TTS=http://localhost:9000/v1
```

### Multiple Models

Download and use multiple models for different purposes:

```bash
# Download additional models
docker compose exec speaches uv tool run speaches-cli model download model-name-1
docker compose exec speaches uv tool run speaches-cli model download model-name-2

# List downloaded models
docker compose exec speaches uv tool run speaches-cli model list
```

In Open Notebook, add each model separately and choose which to use for different podcasts.

## Network Configuration

### Docker Networking

When Open Notebook runs in Docker and needs to reach Speaches:

**On macOS/Windows:**
```bash
export OPENAI_COMPATIBLE_BASE_URL_TTS=http://host.docker.internal:8969/v1
```

**On Linux:**
```bash
# Option 1: Use Docker bridge IP
export OPENAI_COMPATIBLE_BASE_URL_TTS=http://172.17.0.1:8969/v1

# Option 2: Use host networking
docker run --network host ...
```

### Remote Speaches Server

Run Speaches on a different machine for distributed processing:

```bash
# On the server machine
docker compose up -d

# Allow external connections (be careful with firewall settings)
# Update docker-compose.yml to bind to 0.0.0.0:8969
```

Then configure Open Notebook:
```bash
export OPENAI_COMPATIBLE_BASE_URL_TTS=http://server-ip:8969/v1
```

**Security Warning:** Only expose Speaches on trusted networks or use proper authentication/firewall rules.

## Podcast Generation

### Creating Podcasts with Local TTS

Once configured, use Speaches for podcast generation:

1. **Go to Podcasts page** in Open Notebook
2. **Create or edit an Episode Profile**
3. **Configure speakers:**
   - For each speaker, select your Speaches model
   - Choose different voices (e.g., `af_bella` for host, `am_adam` for guest)
4. **Generate podcast**
5. **Audio is generated locally** using your Speaches server

### Multi-Speaker Setup

Create natural-sounding conversations with different voices:

```
Speaker 1 (Host):
- Model: speaches-ai/Kokoro-82M-v1.0-ONNX
- Voice: af_bella

Speaker 2 (Guest):
- Model: speaches-ai/Kokoro-82M-v1.0-ONNX
- Voice: am_adam

Speaker 3 (Narrator):
- Model: speaches-ai/Kokoro-82M-v1.0-ONNX
- Voice: bf_emma
```

## Performance Optimization

### CPU Performance

**Recommended Specs:**
- 4+ CPU cores
- 4GB+ RAM
- SSD storage

**Tips:**
- Close unnecessary applications
- Use quantized models when available
- Adjust speech speed for faster generation

### Memory Management

Monitor Docker memory usage:
```bash
docker stats speaches
```

Allocate more memory if needed:
```yaml
services:
  speaches:
    # ... other config ...
    mem_limit: 4g  # Adjust based on your system
```

### Batch Processing

For generating multiple audio files, Speaches handles concurrent requests efficiently. Open Notebook automatically manages this during podcast generation.

## Troubleshooting

### Service Won't Start

**Symptom:** Container exits immediately

**Solutions:**
```bash
# Check logs
docker compose logs speaches

# Verify Docker is running
docker ps

# Check port availability
lsof -i :8969  # macOS/Linux
netstat -ano | findstr :8969  # Windows
```

---

### Connection Refused

**Symptom:** Open Notebook can't reach Speaches

**Solutions:**
1. **Verify Speaches is running:**
   ```bash
   curl http://localhost:8969/v1/models
   ```

2. **Check Docker networking:**
   - Use `host.docker.internal` instead of `localhost` when Open Notebook is in Docker
   - Verify firewall settings

3. **Test from inside Open Notebook container:**
   ```bash
   docker exec -it open-notebook curl http://host.docker.internal:8969/v1/models
   ```

---

### Model Not Found

**Symptom:** Error about missing model during generation

**Solutions:**
1. **Verify model is downloaded:**
   ```bash
   docker compose exec speaches uv tool run speaches-cli model list
   ```

2. **Download the model:**
   ```bash
   docker compose exec speaches uv tool run speaches-cli model download speaches-ai/Kokoro-82M-v1.0-ONNX
   ```

3. **Check model name matches** what you configured in Open Notebook

---

### Poor Audio Quality

**Symptom:** Generated speech sounds robotic or unclear

**Solutions:**
- Try different voices
- Adjust speech speed (1.0 is normal, try 0.9-1.2)
- Use higher-quality models if available
- Check that model downloaded completely

---

### Slow Generation

**Symptom:** Audio generation takes a long time

**Solutions:**
- **Enable GPU acceleration** if you have an NVIDIA GPU
- **Use faster models** (smaller models = faster generation)
- **Adjust speech speed** to 1.5-2.0 for quicker output
- **Allocate more CPU cores** in Docker settings
- **Use SSD storage** instead of HDD

---

### Out of Memory

**Symptom:** Container crashes or system freezes

**Solutions:**
1. **Increase Docker memory limit:**
   ```yaml
   services:
     speaches:
       mem_limit: 4g  # Increase this value
   ```

2. **Use smaller models**
3. **Close other applications**
4. **Monitor with** `docker stats`

---

### Voice Not Available

**Symptom:** Requested voice doesn't work

**Solutions:**
- Check available voices for your model
- Use one of the documented voices (af_bella, am_adam, etc.)
- Verify voice name spelling (case-sensitive)

## Comparison: Local vs Cloud TTS

| Aspect | Local (Speaches) | Cloud (OpenAI/ElevenLabs) |
|--------|------------------|---------------------------|
| **Cost** | Free after setup | $15-50 per 1M characters |
| **Privacy** | Complete | Data sent to provider |
| **Speed** | Depends on hardware | Usually faster |
| **Quality** | Good (improving) | Excellent |
| **Setup** | Moderate complexity | Simple API key |
| **Offline** | Yes | No |
| **Rate Limits** | None | Yes |
| **Voices** | Limited selection | Many options |
| **Languages** | Limited | 50+ languages |

**Recommendation:**
- **Use Local** for: Privacy-sensitive content, high-volume generation, development
- **Use Cloud** for: Production podcasts, multiple languages, premium quality needs

## Best Practices

### 1. Model Management

**Download Models Ahead of Time:**
```bash
# Don't wait until generation time
docker compose exec speaches uv tool run speaches-cli model download speaches-ai/Kokoro-82M-v1.0-ONNX
```

**Keep Models Updated:**
```bash
# Periodically check for model updates
# Remove old models to save space
docker compose exec speaches uv tool run speaches-cli model list
```

### 2. Voice Selection

**Test Before Production:**
- Generate test audio with different voices
- Choose voices that match your podcast style
- Use consistent voices for recurring speakers

**Voice Characteristics:**
- Clear pronunciation for educational content
- Expressive voices for storytelling
- Professional voices for business content

### 3. Resource Management

**Monitor System Resources:**
```bash
# Check Docker resource usage
docker stats speaches

# Monitor disk space for models
docker compose exec speaches df -h
```

**Optimize Docker:**
```yaml
# Set appropriate limits
services:
  speaches:
    mem_limit: 4g
    cpus: 2
```

### 4. Backup Strategy

**Persist Model Cache:**
The `hf-hub-cache` volume stores downloaded models. To backup:
```bash
# List volumes
docker volume ls

# Backup volume
docker run --rm -v hf-hub-cache:/data -v $(pwd):/backup ubuntu tar czf /backup/speaches-models-backup.tar.gz /data
```

**Restore if needed:**
```bash
docker run --rm -v hf-hub-cache:/data -v $(pwd):/backup ubuntu tar xzf /backup/speaches-models-backup.tar.gz -C /
```

### 5. Testing

**Always Test First:**
```bash
# Test with short text before generating long podcasts
curl "http://localhost:8969/v1/audio/speech" -s \
  -H "Content-Type: application/json" \
  --output test.mp3 \
  --data '{
    "input": "Test",
    "model": "speaches-ai/Kokoro-82M-v1.0-ONNX",
    "voice": "af_bella"
  }'
```

## Complete Setup Script

For quick setup, save this as `setup-speaches.sh`:

```bash
#!/bin/bash
set -e

echo "Creating Speaches setup directory..."
mkdir -p speaches-setup
cd speaches-setup

echo "Creating docker-compose.yml..."
cat > docker-compose.yml << 'EOF'
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
EOF

echo "Starting Speaches container..."
docker compose up -d

echo "Waiting for service to be ready..."
sleep 10

echo "Downloading TTS model..."
docker compose exec speaches uv tool run speaches-cli model download speaches-ai/Kokoro-82M-v1.0-ONNX

echo "Testing speech generation..."
curl "http://localhost:8969/v1/audio/speech" -s -H "Content-Type: application/json" \
  --output test-audio.mp3 \
  --data '{
    "input": "Hello! Speaches is now configured and ready to use with Open Notebook.",
    "model": "speaches-ai/Kokoro-82M-v1.0-ONNX",
    "voice": "af_bella",
    "speed": 1.0
  }'

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Test the audio file: test-audio.mp3"
echo "2. Set environment variable: export OPENAI_COMPATIBLE_BASE_URL_TTS=http://localhost:8969/v1"
echo "3. Configure in Open Notebook Settings → Models"
echo ""
echo "To stop Speaches: docker compose down"
echo "To restart: docker compose up -d"
```

Make it executable and run:
```bash
chmod +x setup-speaches.sh
./setup-speaches.sh
```

## Using Other Local TTS Servers

The principles in this guide apply to any OpenAI-compatible TTS server. When using a different solution:

1. **Start your TTS server** following its documentation
2. **Set the environment variable** to point to your server:
   ```bash
   export OPENAI_COMPATIBLE_BASE_URL_TTS=http://your-server-url:port/v1
   ```
3. **Add the model in Open Notebook** using provider `openai_compatible`
4. **Use the model name** as specified by your TTS server

The key requirement is OpenAI API compatibility - specifically, the `/v1/audio/speech` endpoint.

## Getting Help

**Resources:**
- **Open Notebook Discord**: [https://discord.gg/37XJPXfz2w](https://discord.gg/37XJPXfz2w) - Get help with Open Notebook integration
- **Open Notebook Issues**: Report integration issues to Open Notebook
- **Speaches GitHub**: [https://github.com/speaches-ai/speaches](https://github.com/speaches-ai/speaches) - For Speaches-specific questions
- **Your TTS Server Documentation**: Consult the docs for your chosen TTS solution

**Common Questions:**

**Q: Can I use Speaches with multiple Open Notebook instances?**
A: Yes! Just point each instance to the same Speaches server URL.

**Q: How much disk space do I need?**
A: Each model is 300-800MB. Start with 5GB and add more as you download models.

**Q: Can I use this for commercial podcasts?**
A: Check the model's license on Hugging Face. Most open models allow commercial use.

**Q: How does quality compare to ElevenLabs or OpenAI?**
A: Local models are improving rapidly. For most use cases, quality is very good. Premium services still have an edge for the highest quality needs.

## Related Documentation

- **[OpenAI-Compatible Setup](openai-compatible.md)** - General OpenAI-compatible provider configuration
- **[AI Models Guide](ai-models.md)** - Complete AI model configuration
- **[Podcast Generation](podcasts.md)** - Learn about creating podcasts
- **[Ollama Setup](ollama.md)** - Another local AI option for language models

---

This guide should get you up and running with local text-to-speech in Open Notebook. Enjoy complete privacy and unlimited audio generation! 🎙️
