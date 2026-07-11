# oMLX Setup Guide

[oMLX](https://omlx.ai/) is a macOS-native inference server for Apple Silicon. It runs MLX models locally and exposes an **OpenAI-compatible API** at `/v1`, so Open Notebook can use it for language and embedding models without sending data to the cloud.

Open Notebook treats **oMLX** as a first-class provider in Settings → API Keys. Under the hood it uses Esperanto’s `openai-compatible` client (Esperanto has no native `omlx` provider).

## Why Choose oMLX?

- **Apple Silicon optimized** — MLX inference on M-series Macs
- **OpenAI-compatible** — drop-in `/v1/chat/completions` and `/v1/embeddings`
- **Private** — models and prompts stay on your machine
- **Optional API key** — protect the local server with `--api-key` if needed

## Requirements

- Apple Silicon Mac (M1 or later)
- macOS 15+ (Sequoia) recommended
- oMLX installed and running

## Install oMLX

**DMG (recommended):** download from [oMLX Releases](https://github.com/jundot/omlx/releases), drag to Applications, and launch.

**Homebrew:**

```bash
brew tap jundot/omlx
brew install omlx
brew services start omlx
```

**CLI:**

```bash
omlx serve
# or with a custom port (recommended — see Port Conflict below):
OMLX_PORT=11435 omlx serve
```

Admin UI (when using the default port): `http://localhost:8000/admin`

## Port Conflict with SurrealDB

oMLX and SurrealDB both default to **port 8000**. Open Notebook’s database uses `8000`, so running oMLX on the default port will collide.

**Recommended:** run oMLX on **11435** (same idea as Ollama’s 11434):

```bash
OMLX_PORT=11435 omlx serve
```

Or set the port in oMLX’s admin settings / `~/.omlx/settings.json`.

Then use this base URL in Open Notebook:

```text
http://localhost:11435/v1
```

> Always include the `/v1` suffix — oMLX’s OpenAI API lives under `/v1` (e.g. `GET /v1/models`).

## Configure Open Notebook

1. Go to **Settings** → **API Keys**
2. Click **Add Credential** → select **oMLX**
3. Set **Base URL** to `http://localhost:11435/v1` (or your host/port)
4. Optionally set an **API key** if you started oMLX with `--api-key`
5. **Save** → **Test Connection** → **Discover Models** → register language and embedding models

### Legacy env vars (optional fallback)

```bash
# Prefer Settings UI; env is for migration / headless setups
export OMLX_API_BASE=http://localhost:11435/v1
# Optional, only if oMLX was started with --api-key
# export OMLX_API_KEY=your-key
```

## Network Notes (Docker)

If Open Notebook runs in Docker and oMLX runs on the Mac host:

| Setup | Base URL |
|-------|----------|
| Both on host | `http://localhost:11435/v1` |
| Open Notebook in Docker, oMLX on host | `http://host.docker.internal:11435/v1` |

Ensure oMLX listens on an interface Docker can reach (not only a firewalled bind if you need container access).

## Modalities

| Modality | Supported |
|----------|-----------|
| Language | ✅ |
| Embedding | ✅ |
| Speech-to-text | ❌ |
| Text-to-speech | ❌ |

For local STT/TTS, see [Local STT](local-stt.md) and [Local TTS](local-tts.md) (e.g. Speaches via OpenAI-Compatible).

## Troubleshooting

| Symptom | What to check |
|---------|----------------|
| Connection refused | Is oMLX running? Correct port? |
| Wrong port / SurrealDB errors | Don’t use `8000` for oMLX — use `11435` (or another free port) |
| 404 on `/models` | Base URL must end with `/v1` |
| 401 Unauthorized | API key mismatch with oMLX `--api-key` |
| No models listed | Load/download models in the oMLX admin UI first |
| Docker can’t reach host | Use `host.docker.internal` and confirm oMLX bind address |

Quick connectivity check:

```bash
curl http://localhost:11435/v1/models
```

## Related

- [Ollama Setup](ollama.md) — another local provider (native Ollama API)
- [OpenAI-Compatible](openai-compatible.md) — generic OpenAI API servers (LM Studio, vLLM, …)
- [AI Providers](ai-providers.md) — all provider options
- [API Configuration](../3-USER-GUIDE/api-configuration.md) — credentials UI walkthrough
