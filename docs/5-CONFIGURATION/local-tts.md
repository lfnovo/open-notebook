# Local Speech with Speaches (TTS and STT)

Run text-to-speech (podcast voices) and speech-to-text (transcribing audio and video sources) on your own machine, with no per-minute cost and no audio leaving your network.

[Speaches](https://github.com/speaches-ai/speaches) is an open-source server with an OpenAI-compatible speech API. One Speaches instance serves both directions; Open Notebook connects to it through the **OpenAI Compatible** provider. Any other server that implements `/v1/audio/speech` (TTS) or `/v1/audio/transcriptions` (STT) works the same way.

This page covers the shared setup and text-to-speech. Speech-to-text specifics (Whisper models, long recordings) are in [Local Speech-to-Text](local-stt.md).

> **Ready-made compose files:** [docker-compose-speaches.yml](../../examples/docker-compose-speaches.yml) (Speaches + Open Notebook) and [docker-compose-full-local.yml](../../examples/docker-compose-full-local.yml) (Speaches + Ollama + Open Notebook, fully local).

---

## 1. Run Speaches

Standalone:

```yaml
services:
  speaches:
    image: ghcr.io/speaches-ai/speaches:latest-cpu
    ports:
      - "8969:8000"
    volumes:
      - hf-hub-cache:/home/ubuntu/.cache/huggingface/hub
    restart: unless-stopped

volumes:
  hf-hub-cache:
```

For an NVIDIA GPU, use the `latest-cuda` image and add a GPU reservation:

```yaml
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
```

If you add the `speaches` service to Open Notebook's own `docker-compose.yml` instead, Open Notebook reaches it at `http://speaches:8000/v1` and you don't need to publish a port.

## 2. Download models

```bash
docker compose up -d

# Text-to-speech voice model
docker compose exec speaches uv tool run speaches-cli model download speaches-ai/Kokoro-82M-v1.0-ONNX

# Speech-to-text model (see local-stt.md for other sizes)
docker compose exec speaches uv tool run speaches-cli model download Systran/faster-whisper-small
```

Test text-to-speech:

```bash
curl http://localhost:8969/v1/audio/speech -s -H "Content-Type: application/json" \
  --output test.mp3 \
  --data '{"input": "Local speech is working.", "model": "speaches-ai/Kokoro-82M-v1.0-ONNX", "voice": "af_bella"}'
```

## 3. Connect Open Notebook

1. **Manage → Models** → **OpenAI Compatible** section → **Add Configuration**.
2. **Configuration Name** "Speaches", no API key, **Base URL**:

   | Open Notebook runs | Base URL |
   |--------------------|----------|
   | In Docker, Speaches published on the host (macOS/Windows) | `http://host.docker.internal:8969/v1` |
   | In Docker on Linux | `http://host.docker.internal:8969/v1` with `extra_hosts: ["host.docker.internal:host-gateway"]` on the `open_notebook` service, or `http://172.17.0.1:8969/v1` |
   | In the same compose file as Speaches | `http://speaches:8000/v1` |
   | From source | `http://localhost:8969/v1` |
   | Speaches on another machine | `http://<server-ip>:8969/v1` |

3. Click **Test**, then **Models**. In **Discover Models**, set **Model Type** to **TTS** and add `speaches-ai/Kokoro-82M-v1.0-ONNX`; then set it to **STT** and add your Whisper model. If a model isn't listed, type its id and click **Add "…"**.
4. Under **Default Model Assignments**, choose the **Text-to-Speech Model** and **Speech-to-Text Model**.

If you also use another OpenAI-compatible server (LM Studio, vLLM) for chat, keep it as a separate configuration: each configuration has one Base URL.

## 4. Use it for podcasts

Podcast voices come from **speaker profiles** (Podcasts → Profiles). In each speaker profile, select the Speaches model as the voice model and set **Voice ID** to a Kokoro voice, for example `af_bella` or `am_adam`. The voice list is in the Speaches and Kokoro documentation. The speaker profiles that ship with Open Notebook use OpenAI voice names and have no voice model set, so edit them before generating.

Local TTS servers usually handle one request at a time. If podcast audio fails or stalls, lower `TTS_BATCH_SIZE` (default 5) to `1` or `2`, and raise `ESPERANTO_TTS_TIMEOUT` (default 300 seconds) for long segments on CPU. Both go in the `open_notebook` environment; see the [Environment Reference](environment-reference.md#worker-and-background-jobs).

---

## Troubleshooting

**Test shows "Cannot connect to server. Check the URL is correct."** Check that Speaches runs (`curl http://localhost:8969/v1/models` on the host), then from inside the container:

```bash
docker compose exec open_notebook curl -s http://host.docker.internal:8969/v1/models
```

**Model not found.** List what Speaches has downloaded and download the missing model:

```bash
docker compose exec speaches uv tool run speaches-cli model list
```

**Podcast fails with a voice error.** The speaker profile's Voice ID isn't a voice the model provides. See [Processing Issues → Podcasts](../6-TROUBLESHOOTING/processing-issues.md#podcast-failures).

**Slow generation.** Use the `latest-cuda` image on a GPU, give the container more CPU, and keep `TTS_BATCH_SIZE` low.

---

## Related

- [Local Speech-to-Text](local-stt.md) — Whisper models, long audio
- [OpenAI-Compatible Providers](openai-compatible.md)
- [Creating Podcasts](../3-USER-GUIDE/creating-podcasts.md)
