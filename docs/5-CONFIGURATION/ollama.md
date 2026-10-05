# Ollama Setup Guide

[Ollama](https://ollama.com) runs open-weight models on your own hardware. Open Notebook can use it for chat, transformations, podcast scripts and embeddings. It doesn't provide speech models; for local podcasts and transcription, add [Speaches](local-tts.md).

---

## Quick Start

### 1. Install Ollama and pull models

```bash
# Linux / macOS
curl -fsSL https://ollama.com/install.sh | sh
# Windows: download the installer from https://ollama.com/download

# A language model (pick one that fits your hardware)
ollama pull qwen3

# An embedding model (needed for search, Ask and embeddings)
ollama pull mxbai-embed-large
```

Open Notebook doesn't download Ollama models for you. Pull every model you plan to use, including the embedding model.

### 2. Let Open Notebook reach Ollama

If Open Notebook runs in Docker or on another machine, Ollama must listen on more than localhost:

```bash
OLLAMA_HOST=0.0.0.0:11434 ollama serve
```

For the systemd service on Linux, run `sudo systemctl edit ollama`, add these lines, save, then run `sudo systemctl restart ollama`:

```ini
[Service]
Environment="OLLAMA_HOST=0.0.0.0:11434"
```

`OLLAMA_HOST=0.0.0.0` exposes Ollama's API, which has no authentication, on every network interface. Allow port 11434 only from this host and its Docker networks (for example with your firewall), never from untrusted networks. On macOS and Windows with Docker Desktop, try without this first: `host.docker.internal` usually reaches Ollama's default setup. See [Docker Compose installation](../1-INSTALLATION/docker-compose.md) for the per-platform steps.

### 3. Add the credential

Follow [Connect a provider](../4-AI-PROVIDERS/index.md#connect-a-provider) and pick **Ollama**. No API key is needed; set **Base URL** from the table below. In **Discover Models**, add your chat model with **Model Type** `Language` and your embedding model with `Embedding`.

---

## Which Base URL to use

| Open Notebook runs | Ollama runs | Base URL |
|--------------------|-------------|----------|
| From source on the same machine | Same machine | `http://localhost:11434` |
| In Docker | On the host | `http://host.docker.internal:11434` |
| In Docker | In the same compose file (service `ollama`) | `http://ollama:11434` |
| Anywhere | Another machine | `http://<ollama-ip>:11434` |

**Linux with Docker:** `host.docker.internal` doesn't exist by default. Add it to the `open_notebook` service, then `docker compose up -d`:

```yaml
services:
  open_notebook:
    extra_hosts:
      - "host.docker.internal:host-gateway"
```

Without it, Test shows "Cannot connect to Ollama. Check if Ollama server is running." and the log shows `Name or service not known`.

### Ollama in the same compose file

Add a service next to `surrealdb` and `open_notebook` in the shipped `docker-compose.yml`:

```yaml
services:
  ollama:
    image: ollama/ollama:latest
    volumes:
      - ./ollama_data:/root/.ollama
    # GPU (NVIDIA Container Toolkit required)
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
```

Use Base URL `http://ollama:11434`, and pull models inside the container: `docker compose exec ollama ollama pull qwen3`. The repository's `examples/docker-compose-ollama.yml` is a complete version of this setup.

---

## GPU acceleration

- **Ollama in Docker with an NVIDIA GPU:** install the [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html) on the host and add the `deploy.resources.reservations.devices` block shown in [Ollama in the same compose file](#ollama-in-the-same-compose-file). Without it, the container runs on CPU only.
- **Ollama installed on the host:** it uses a supported GPU (NVIDIA CUDA, Apple Silicon Metal, AMD ROCm) on its own; nothing to configure in Open Notebook.

`ollama ps` shows whether a loaded model runs on the GPU or the CPU.

## Model names

Discover Models lists the models Ollama has installed, so the names come out right. If you type a name by hand, it must match `ollama list` exactly, tag included:

```
$ ollama list
NAME                        SIZE
mxbai-embed-large:latest    669 MB
gemma3:12b                  8.1 GB
```

Use `gemma3:12b`, not `gemma3`. If you remove a model from Ollama, remove it from Manage → Models too and pick new defaults.

---

## Context window (`num_ctx`)

Ollama credentials have a **Context Window (num_ctx)** field. Empty means 8192 tokens, which runs on GPUs with about 8 GB of VRAM. It applies to every model used through that credential.

Ollama doesn't return an error when a prompt is longer than the window: it drops the start of the prompt and answers anyway (its server log shows a `truncating input prompt` warning). Symptoms in Open Notebook are answers that ignore your sources, chats that forget earlier messages, and transformations of long documents that only cover the end.

To fix it, edit the Ollama credential in Manage → Models and raise **Context Window (num_ctx)**, for example to `32768`, if your hardware has the memory for it. If Ollama then runs out of memory or becomes very slow, lower it again or use a smaller model. Including fewer sources in chat context ("Insights only" instead of "Full content") also helps.

---

## Timeouts with slow models

Every model call is limited by `ESPERANTO_LLM_TIMEOUT`, **180 seconds** by default. Before v1.15.0 Ollama calls had no time limit; now a large model on CPU, or the first request while a model loads into memory, can run out of time. When that happens, the error says:

> The AI provider took too long to respond. Try again, use a faster model, or raise ESPERANTO_LLM_TIMEOUT (180 seconds by default).

(v1.15.0 shows "Could not connect to the AI provider. Please check your network connection and provider URL." for the same timeout.)

Raise the limit in the `open_notebook` service, keeping it below 600 seconds (the web UI's own limit), and apply with `docker compose up -d`:

```yaml
services:
  open_notebook:
    environment:
      - ESPERANTO_LLM_TIMEOUT=420
      - OPEN_NOTEBOOK_WORKER_MAX_TASKS=1   # one job at a time on a single GPU
```

`OPEN_NOTEBOOK_WORKER_MAX_TASKS=1` stops background jobs (source processing, embeddings, insights, podcasts) from sending several requests to Ollama at once, which makes each of them slower and more likely to time out. To keep a model loaded between requests, set `OLLAMA_KEEP_ALIVE` on the Ollama server (for example `30m`).

---

## Troubleshooting

### Test shows "Cannot connect to Ollama. Check if Ollama server is running."

1. Is Ollama running? `curl http://localhost:11434/api/tags` on the Ollama machine.
2. Is it listening beyond localhost? See [step 2](#2-let-open-notebook-reach-ollama) (and its exposure warning).
3. Can the container reach it?
   ```bash
   docker compose exec open_notebook curl -s http://host.docker.internal:11434/api/tags
   ```
   On Linux, add the `extra_hosts` entry shown above. If a firewall blocks the container, allow port 11434 only from the Docker networks, for example `sudo ufw allow from 172.16.0.0/12 to any port 11434 proto tcp` (check your Docker subnets with `docker network inspect`), never from everywhere.

### "Connection timed out. Check if Ollama server is accessible."

The address resolves but nothing answers: wrong IP, a firewall dropping packets, or a VPN between the machines.

### "No model configured for default for type=chat"

No Chat Model is assigned. Go to **Manage → Models → Default Model Assignments**.

### "Model is not a LanguageModel: …"

An embedding model is assigned to a language role (Chat, Transformation, Tools or Large Context Model). Assign a language model there; embedding models belong only in Embedding Model.

### Answers ignore the sources, or long documents are cut short

The prompt is bigger than the context window. See [Context window](#context-window-num_ctx).

### Chat or transformations fail after a few minutes

Timeout. See [Timeouts with slow models](#timeouts-with-slow-models).

### Self-signed certificate on an HTTPS Ollama endpoint

`[SSL: CERTIFICATE_VERIFY_FAILED]`: mount your CA bundle and set `ESPERANTO_SSL_CA_BUNDLE`, as described in [Advanced → SSL](advanced.md#ssl-for-self-signed-providers).

---

## Legacy environment variable

`OLLAMA_API_BASE` still works as a deprecated fallback when no Ollama credential exists. Use the credential instead; **Migrate to Database** in **Manage → Models** converts it. See the [Environment Reference](environment-reference.md#legacy-ai-provider-variables-deprecated).

---

## Related

- [AI Providers](ai-providers.md) — other providers, including embedding providers to pair with Ollama
- [Local speech with Speaches](local-tts.md) — local TTS and STT
- [OpenAI-Compatible](openai-compatible.md) — LM Studio, vLLM, llama.cpp
- [AI & Chat Issues](../6-TROUBLESHOOTING/ai-chat-issues.md)
