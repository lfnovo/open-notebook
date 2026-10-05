# Quick Start - Local & Private (10 minutes)

Run Open Notebook and **Ollama** together in Docker. No cloud API keys: your content is processed by models on your machine, not sent to an AI provider. To keep the app itself private, make sure other devices can't reach it (see the note in Step 1).

**Already have Ollama installed on this computer?** Use the [External Ollama guide](quick-start-external-ollama.md) instead.

## Prerequisites

- **Docker with Compose v2**: [Docker Desktop](https://www.docker.com/products/docker-desktop/) on macOS and Windows; Docker Engine with the Compose plugin on Linux.
- **8 GB of RAM or more.** Local models run on your CPU unless you set up GPU access, and small models are noticeably slower than cloud ones.
- A few GB of disk for the models.

## Step 1: Download and configure (1 min)

```bash
mkdir open-notebook
cd open-notebook
curl -o docker-compose.yml https://raw.githubusercontent.com/lfnovo/open-notebook/main/docker-compose.yml
```

(On Windows PowerShell, use `curl.exe`.)

Open `docker-compose.yml` and replace `change-me-to-a-secret-string` in the `OPEN_NOTEBOOK_ENCRYPTION_KEY` line with a long random secret you generate yourself, for example with `openssl rand -hex 32` (Windows: see [Set your encryption key](../1-INSTALLATION/docker-compose.md#step-2-set-your-encryption-key)). Don't reuse an example value.

> **Shared network or server?** The shipped file publishes the UI (`8502`) and API (`5055`) on all network interfaces, and there is no password by default. If other devices can reach this machine, do one of these before starting: change the two `open_notebook` port lines to `"127.0.0.1:8502:8502"` and `"127.0.0.1:5055:5055"`, or add `- OPEN_NOTEBOOK_PASSWORD=your-password` to its `environment:` block.

## Step 2: Add the Ollama service (1 min)

Create a file named `docker-compose.override.yml` in the same folder. Docker Compose merges it with `docker-compose.yml` automatically:

```yaml
services:
  ollama:
    image: ollama/ollama:latest
    volumes:
      - ./ollama_models:/root/.ollama
    restart: always
```

For NVIDIA GPU access, see [GPU acceleration](../5-CONFIGURATION/ollama.md#gpu-acceleration) in the Ollama guide.

## Step 3: Start (1 min)

```bash
docker compose up -d
```

## Step 4: Download models (2-5 min)

Open Notebook needs a **chat model** and an **embedding model**. Nothing downloads them automatically:

```bash
docker compose exec ollama ollama pull qwen3
docker compose exec ollama ollama pull nomic-embed-text
```

`qwen3` is a capable general model of about 5 GB. On a smaller machine, try `llama3.2` (about 2 GB) or `gemma3:1b` instead. Browse more at [ollama.com/library](https://ollama.com/library).

Check what's installed with `docker compose exec ollama ollama list`.

## Step 5: Connect Ollama and chat (3 min)

Open **http://localhost:8502** and follow **[Connect a provider](../4-AI-PROVIDERS/index.md#connect-a-provider)** with these values:

| Field | Value |
|---|---|
| Provider | **Ollama** |
| API Key | Leave empty |
| Base URL | `http://ollama:11434` |
| Models to add | Your chat model as **Language** (Ollama lists it as `qwen3:latest`), then `nomic-embed-text:latest` as **Embedding** |
| Defaults | Click **Auto-assign Defaults** |

The last step of that page creates a notebook, adds a text source and sends a chat message. The first answer can take a while as Ollama loads the model.

## Verification checklist

- [ ] `docker compose ps` shows `surrealdb`, `open_notebook` and `ollama` running
- [ ] `docker compose exec ollama ollama list` shows a chat model and `nomic-embed-text`
- [ ] **Test** on the Ollama configuration shows a green check
- [ ] **Default Model Assignments** has a Chat Model and an Embedding Model
- [ ] A chat message gets an answer

## Troubleshooting

**Test shows a red cross.** The base URL must be `http://ollama:11434` (the service name), not `localhost`: inside the Open Notebook container, `localhost` is the container itself. Also check that you pulled at least one model; the test uses one.

**Responses are very slow or time out.** Small models on CPU are slow. Try a smaller model, enable GPU access, or set `OPEN_NOTEBOOK_WORKER_MAX_TASKS=1` so background jobs don't compete with chat. Timeouts are covered in the [Ollama guide](../5-CONFIGURATION/ollama.md).

**Adding more models later.** Run `docker compose exec ollama ollama pull <model>`, then click **Models** on the Ollama configuration again (it opens the **Discover Models** dialog) and add it.

**Anything else.** `docker compose logs -f open_notebook` and `docker compose logs -f ollama`. See [Quick Fixes](../6-TROUBLESHOOTING/quick-fixes.md).

## Podcasts and audio, locally

Ollama provides chat and embedding models only. For podcasts (text-to-speech) and audio/video transcription (speech-to-text) without the cloud, run a local speech server and add it as **OpenAI Compatible**: see [Local TTS](../5-CONFIGURATION/local-tts.md) and [Local STT](../5-CONFIGURATION/local-stt.md). You can also mix: local chat with a cloud TTS provider.

## LM Studio instead of Ollama

LM Studio runs on your computer, outside Docker:

1. In LM Studio, download a chat model and an embedding model and start the local server (default port 1234).
2. Skip Steps 2 and 4 above. On Linux, add this to `docker-compose.override.yml` so the container can reach your computer:

   ```yaml
   services:
     open_notebook:
       extra_hosts:
         - "host.docker.internal:host-gateway"
   ```

3. [Connect a provider](../4-AI-PROVIDERS/index.md#connect-a-provider) using **OpenAI Compatible**, with Base URL `http://host.docker.internal:1234/v1`.

More in [OpenAI-Compatible Providers](../5-CONFIGURATION/openai-compatible.md).

## Next steps

- [Ollama guide](../5-CONFIGURATION/ollama.md): model choices, GPU, networking, timeouts
- [Docker Compose guide](../1-INSTALLATION/docker-compose.md): settings, backups, updates
- [User Guide](../3-USER-GUIDE/index.md)

**Need help?** Join our [Discord community](https://discord.gg/37XJPXfz2w).
