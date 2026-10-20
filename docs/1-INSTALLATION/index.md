# Installation Guide

Pick the route that fits your setup. All of them end the same way: open the UI and [connect a provider](../4-AI-PROVIDERS/index.md#connect-a-provider).

| Route | For | You need |
|---|---|---|
| **[Docker Compose](docker-compose.md)** (recommended) | Almost everyone: laptops, home servers, VPS | Docker with Compose v2 |
| [From Source](from-source.md) | Developers and contributors | Python 3.11–3.12, uv, Node.js 20.9+, Docker (for the database), ffmpeg |
| [Windows Native](windows-native.md) | Windows machines that can't run Docker or WSL (for example ARM64) | Python 3.11–3.12 via uv, Node.js 20.9+, SurrealDB 2.x, ffmpeg |
| [Single Container](single-container.md) (deprecated) | Hosting platforms that run one container per app; removed in v2 | Docker or a container host with persistent storage |

Want a guided first run with a specific provider? The [quick starts](../0-START-HERE/index.md) wrap the Docker Compose route with provider-specific steps (cloud API key, Ollama in Docker, Ollama on the host).

---

## System requirements

- **RAM:** 4 GB free at minimum, 8 GB or more recommended. Local models need much more (see [Ollama](../5-CONFIGURATION/ollama.md)).
- **Disk:** room for the Docker images, your documents and any local models.
- **GPU:** optional. It only matters for local models.
- **Network:** needed to pull images and to reach cloud AI providers. With local models, Open Notebook works offline once installed.

## AI providers

You need at least one provider for chat, and an embedding model for search. You configure them in the UI after installing, not in config files.

- **Cloud providers** (OpenAI, Anthropic, Google, Mistral, OpenRouter and many more): pay per use; your content is sent to the provider.
- **Local providers** (Ollama, oMLX, LM Studio, or another OpenAI-compatible server running on your own hardware): free to run; content stays on your hardware; speed depends on your hardware. An OpenAI-compatible endpoint hosted elsewhere is a cloud provider for privacy purposes.

The full list, with which providers cover chat, embeddings and speech, is in [AI Providers](../4-AI-PROVIDERS/index.md).

---

## After installing

1. [Connect a provider](../4-AI-PROVIDERS/index.md#connect-a-provider) and set the default models. Chat doesn't work until you do.
2. Create a notebook and add sources: [User Guide](../3-USER-GUIDE/index.md).

## Before exposing it to a network

The defaults are for a single user on a trusted machine: authentication is off and CORS is open.

- Set `OPEN_NOTEBOOK_PASSWORD`: [Security](../5-CONFIGURATION/security.md)
- Put it behind HTTPS: [Reverse Proxy](../5-CONFIGURATION/reverse-proxy.md)
- Make sure the browser can reach the API: [Access from another machine](docker-compose.md#access-from-another-machine)

## Need help?

- [Quick Fixes](../6-TROUBLESHOOTING/quick-fixes.md)
- [Discord](https://discord.gg/37XJPXfz2w)
- [GitHub Issues](https://github.com/lfnovo/open-notebook/issues)
