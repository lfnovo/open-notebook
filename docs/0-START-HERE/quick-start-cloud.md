# Quick Start - Cloud AI Providers (5 minutes)

Run Open Notebook with a cloud AI provider such as **OpenAI, Anthropic, Google, Mistral, Groq or OpenRouter**. You need Docker and an API key.

## Prerequisites

1. **Docker with Compose v2**: [Docker Desktop](https://www.docker.com/products/docker-desktop/) on macOS and Windows; Docker Engine with the Compose plugin on Linux.
2. **An API key** from your provider, for example:
   - [OpenAI](https://platform.openai.com/api-keys)
   - [Anthropic](https://console.anthropic.com/settings/keys)
   - [Google AI Studio](https://aistudio.google.com/app/apikey)
   - [Mistral](https://console.mistral.ai/api-keys/)
   - [Groq](https://console.groq.com/keys)
   - [OpenRouter](https://openrouter.ai/keys)

   Other providers are listed in [AI Providers](../4-AI-PROVIDERS/index.md#supported-providers).

> **Pick a provider that does embeddings, or add a second one.** Open Notebook needs a language model for chat **and** an embedding model for search. OpenAI, Google AI, Mistral AI and OpenRouter offer both. Anthropic, DeepSeek and Groq offer no embedding models, so pair them with one that does (for example OpenAI, Google AI, Mistral AI or Voyage AI).

## Step 1: Download and configure (1 min)

```bash
mkdir open-notebook
cd open-notebook
curl -o docker-compose.yml https://raw.githubusercontent.com/lfnovo/open-notebook/main/docker-compose.yml
```

(On Windows PowerShell, use `curl.exe`.)

Open `docker-compose.yml` and replace `change-me-to-a-secret-string` in the `OPEN_NOTEBOOK_ENCRYPTION_KEY` line with a long random secret you generate yourself, for example with `openssl rand -hex 32` (Windows: see [Set your encryption key](../1-INSTALLATION/docker-compose.md#step-2-set-your-encryption-key)). Don't reuse an example value. Keep it: if it changes, saved API keys can't be decrypted.

> **Shared network or server?** The shipped file publishes the UI (`8502`) and API (`5055`) on all network interfaces, and there is no password by default. If other devices can reach this machine, do one of these before starting: change the two `open_notebook` port lines to `"127.0.0.1:8502:8502"` and `"127.0.0.1:5055:5055"`, or add `- OPEN_NOTEBOOK_PASSWORD=your-password` to its `environment:` block.

## Step 2: Start (1 min)

```bash
docker compose up -d
```

Wait about 30 seconds, then open **http://localhost:8502**.

## Step 3: Connect your provider and chat (3 min)

Follow **[Connect a provider](../4-AI-PROVIDERS/index.md#connect-a-provider)** with these values:

| Field | Value |
|---|---|
| Provider | The one you have a key for (for example **OpenAI**) |
| API Key | Your key |
| Base URL | Leave empty |
| Models to add | At least one **Language** model and one **Embedding** model (from this provider or a second one) |
| Defaults | Click **Auto-assign Defaults** |

The last step of that page creates a notebook, adds a text source and sends a chat message. When you get an answer, you're set up.

## Verification checklist

- [ ] `docker compose ps` shows `surrealdb` and `open_notebook` running
- [ ] http://localhost:8502 opens
- [ ] **Test** on your provider configuration shows a green check
- [ ] **Default Model Assignments** has a Chat Model and an Embedding Model
- [ ] A chat message gets an answer

## Optional: podcasts and audio

- **Podcasts** need a **Text-to-Speech Model**. Add a TTS model (OpenAI, Google AI, Mistral AI, xAI, MiniMax, ElevenLabs and others offer them) and pick it under **Default Model Assignments**. Auto-assign doesn't set it.
- **Audio and video sources** need a **Speech-to-Text Model** (OpenAI, Google AI, Groq, Mistral AI, ElevenLabs, Deepgram and others).

## Troubleshooting

**Test shows a red cross.** Check the key on the provider's website and that the account has credit. Edit the configuration to fix the key.

**A model you want isn't in the list.** Type its exact name in the search box of the **Discover Models** dialog and add it as a custom model.

**Chat fails with "No model configured…".** A default model is empty; see [Set default models](../4-AI-PROVIDERS/index.md#4-set-default-models).

**Port 8502 is in use.** In `docker-compose.yml` change `"8502:8502"` to `"8503:8502"`, run `docker compose up -d` and open http://localhost:8503.

**Anything else.** `docker compose logs -f open_notebook` shows the UI, API and worker logs. See [Quick Fixes](../6-TROUBLESHOOTING/quick-fixes.md).

## Next steps

- [Docker Compose guide](../1-INSTALLATION/docker-compose.md): changing settings, backups, updates, access from other machines
- [User Guide](../3-USER-GUIDE/index.md): sources, chat, notes, podcasts
- Before exposing Open Notebook to a network, set a password: [Security](../5-CONFIGURATION/security.md)

**Need help?** Join our [Discord community](https://discord.gg/37XJPXfz2w).
