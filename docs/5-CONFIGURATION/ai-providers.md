# AI Providers - Configuration Guide

Open Notebook supports 24 AI providers. You connect them in the web UI under **Manage → Models**; their keys are stored encrypted in the database.

> **Prerequisite:** `OPEN_NOTEBOOK_ENCRYPTION_KEY` must be set before you can save a provider key. See [Security](security.md#api-key-encryption).

---

## Setting up any provider

The step-by-step procedure (Add Configuration → Test → Models → Default Model Assignments) is in [Connect a provider](../4-AI-PROVIDERS/index.md#connect-a-provider). What differs between providers is the form:

- **API-key providers** (most cloud providers): get a key from the link in the table below (the form also shows a **Get API Key** link). Leave **Base URL** empty unless you need a regional or self-hosted endpoint.
- **Google Vertex AI**: no API key; the form asks for a project, a region and an optional service-account file. See [Google Vertex AI](#google-vertex-ai).
- **Anthropic Compatible**: needs both an **API Key** and a **Base URL** (the service's API root); there is no default endpoint. See [Anthropic Compatible](#anthropic-compatible).
- **Ollama, oMLX and OpenAI Compatible**: the API key is optional; **Base URL** is what matters. See [Ollama](ollama.md), [oMLX](omlx.md) and [OpenAI-Compatible](openai-compatible.md).

When **Test** fails, it shows the reason, for example "Invalid API key" or "Cannot connect to server. Check the URL is correct." (see [AI & Chat Issues → Test fails](../6-TROUBLESHOOTING/ai-chat-issues.md#test-fails)). In the **Discover Models** dialog, a model that isn't listed can be added by typing its exact id in the search box and clicking **Add "…"**.

Chat fails until a **Chat Model** is assigned, and search, Ask and embedding need an **Embedding Model**. Podcasts need a text-to-speech model on each speaker profile.

You can add several configurations per provider (for example separate keys for work and personal use). Each registered model belongs to the configuration it was discovered from.

---

## Providers and what they offer

The modalities are what a new configuration offers by default. If your main provider has no embedding or speech models, add a second provider for those.

| Provider (as shown in the UI) | Language | Embedding | Speech-to-text | Text-to-speech | Get a key |
|-------------------------------|:-:|:-:|:-:|:-:|-----------|
| OpenAI | ✓ | ✓ | ✓ | ✓ | [platform.openai.com](https://platform.openai.com/api-keys) |
| Anthropic | ✓ | | | | [console.anthropic.com](https://console.anthropic.com/settings/keys) |
| Google AI (Gemini) | ✓ | ✓ | ✓ | ✓ | [aistudio.google.com](https://aistudio.google.com/app/apikey) |
| Google Vertex AI | ✓ | ✓ | | ✓ | [Google Cloud](https://cloud.google.com/vertex-ai/docs/start/cloud-environment) |
| Azure OpenAI | ✓ | ✓ | ✓ | ✓ | [Azure portal](https://portal.azure.com/#view/Microsoft_Azure_ProjectOxford/CognitiveServicesHub/~/OpenAI) |
| Groq | ✓ | | ✓ | | [console.groq.com](https://console.groq.com/keys) |
| Mistral AI | ✓ | ✓ | ✓ | ✓ | [console.mistral.ai](https://console.mistral.ai/api-keys/) |
| DeepSeek | ✓ | | | | [platform.deepseek.com](https://platform.deepseek.com/api_keys) |
| xAI (Grok) | ✓ | | | ✓ | [console.x.ai](https://console.x.ai/) |
| OpenRouter | ✓ | ✓ | ✓ | ✓ | [openrouter.ai](https://openrouter.ai/keys) |
| DashScope (Qwen) | ✓ | | | | [Alibaba Model Studio](https://help.aliyun.com/zh/model-studio/getting-started/) |
| MiniMax | ✓ | | | ✓ | [platform.minimaxi.com](https://platform.minimaxi.com/document/Guides) |
| Novita | ✓ | | | | [novita.ai](https://novita.ai/settings/key-management) |
| SiliconFlow | ✓ | | | | [cloud.siliconflow.com](https://cloud.siliconflow.com/account/ak) |
| Z.ai | ✓ | | | | [z.ai](https://z.ai/manage-apikey/apikey-list) |
| PayPerQ | ✓ | ✓ | ✓ | ✓ | [ppq.ai](https://ppq.ai) |
| Cohere | ✓ | ✓ | | | [dashboard.cohere.com](https://dashboard.cohere.com/api-keys) |
| Voyage AI | | ✓ | | | [dash.voyageai.com](https://dash.voyageai.com/api-keys) |
| ElevenLabs | | | ✓ | ✓ | [elevenlabs.io](https://elevenlabs.io/app/settings/api-keys) |
| Deepgram | | | ✓ | ✓ | [console.deepgram.com](https://console.deepgram.com/) |
| Ollama | ✓ | ✓ | | | local, see [Ollama](ollama.md) |
| oMLX | ✓ | ✓ | | | local, see [oMLX](omlx.md) |
| OpenAI Compatible | ✓ | ✓ | ✓ | ✓ | your server, see [OpenAI-Compatible](openai-compatible.md) |
| Anthropic Compatible | ✓ | | | | your server |

This page doesn't list models or prices: they change faster than the docs. **Discover Models** shows what your key can access, and each provider's site has current pricing.

---

## Cloud Providers

### OpenAI

Covers every modality with one key, which makes it the simplest single-provider setup: chat, embeddings, podcast voices and transcription. Keys are created at [platform.openai.com](https://platform.openai.com/api-keys); the account needs credit.

### Anthropic (Claude)

Language models only. Pair it with another provider for embeddings (and for speech if you want podcasts or transcription).

### Anthropic Compatible

For services that implement the Anthropic Messages API at their own URL. Enter the API key and the **Base URL** (the API root, with or without a trailing `/v1`). Language models only. If the endpoint doesn't list models, add the model id by hand in the Discover Models dialog.

### Google Gemini

Shown as **Google AI** in the UI. Uses a Gemini API key from Google AI Studio and offers all four modalities.

### Google Vertex AI

Uses Google Cloud instead of an API key. The form asks for **GCP Project ID**, **Region** and **Service Account JSON Path**, the path to the service-account file **inside the container** (mount it as a volume).

### Groq

Fast hosted inference of open-weight models; language and speech-to-text.

### Mistral AI

Language, embedding and speech models from one key.

### DeepSeek

Language models only.

### xAI (Grok)

Language and text-to-speech.

### OpenRouter

One key for models from many vendors, with unified billing. Model ids include the vendor (`vendor/model`). OpenRouter also serves speech models; Discover Models suggests `microsoft/mai-voice-2` for text-to-speech (it uses Microsoft neural voice names such as `en-US-AvaNeural`, not OpenAI's `alloy`/`nova`) and `openai/whisper-1` / `openai/whisper-large-v3` for speech-to-text.

### DashScope (Qwen)

Alibaba Cloud's Qwen models; language only.

### MiniMax

Language models (`MiniMax-M3` with a 1M-token context, also used for the connection test) and text-to-speech (`speech-2.8-hd`, `speech-2.8-turbo`; Discover Models lists both).

- **Voices:** in a speaker profile, set **Voice ID** to a MiniMax voice id such as `English_Graceful_Lady`. System voices and voices you cloned or designed in your MiniMax account all work.
- **Region:** MiniMax keys are region-specific. Mainland China keys need **Base URL** `https://api.minimax.cn/v1`; the default is the international `https://api.minimax.io/v1`. The same Base URL is used for chat and speech.

### Novita

An OpenAI-compatible gateway for open-weight language models.

### SiliconFlow

Hosted DeepSeek, Qwen, GLM and Kimi models; language only. Mainland China accounts need **Base URL** `https://api.siliconflow.cn/v1` (default: the global `https://api.siliconflow.com/v1`). Keys from one site don't work against the other.

### Z.ai

GLM language models through an OpenAI-compatible API. If a model is missing from Discover Models, type its id (for example `glm-4.5-flash`) and add it by hand.

### PayPerQ (PPQ)

A pay-as-you-go gateway offering language, embedding and speech models. Discovered models are classified by name; check the **Model Type** you add them under.

### Cohere

Language (`command-a-03-2025` is used for the connection test) and embedding models through Cohere's own v2 API. Reranking is not used by Open Notebook.

### Voyage AI

Embedding models only. A common choice next to a language-only provider such as Anthropic.

### ElevenLabs

Text-to-speech and speech-to-text. In speaker profiles, use ElevenLabs voice ids.

### Deepgram

Text-to-speech and speech-to-text.

---

## Self-Hosted / Local

### Ollama (Recommended for Local)

Free local language and embedding models. Enter the server address as **Base URL**, for example `http://host.docker.internal:11434` when Open Notebook runs in Docker and Ollama on the host. Ollama credentials also have a **Context Window (num_ctx)** field (default 8192 tokens).

Networking, model names, context window and the 180-second timeout are covered in the [Ollama guide](ollama.md).

### oMLX (Apple Silicon)

An MLX inference server for M-series Macs, for language and embedding models. Run it on port 11435 (its default 8000 collides with SurrealDB). See the [oMLX guide](omlx.md).

### LM Studio (Local Alternative)

Use the **OpenAI Compatible** provider with **Base URL** `http://host.docker.internal:1234/v1` (Open Notebook in Docker) or `http://localhost:1234/v1` (from source). No API key is needed. See [OpenAI-Compatible](openai-compatible.md#lm-studio).

### Other OpenAI-compatible servers

vLLM, llama.cpp, LocalAI, Text Generation WebUI and Speaches all work through **OpenAI Compatible**. See [OpenAI-Compatible](openai-compatible.md) and, for speech, [Local speech with Speaches](local-tts.md).

---

## Enterprise

### Azure OpenAI

1. Create an Azure OpenAI resource and deploy the models you need.
2. In Manage → Models, add an **Azure OpenAI** configuration with the **API Key**, and put the resource endpoint (`https://<resource>.openai.azure.com`) in **Base URL**.
3. Register models by **deployment name**.

The form has no field for the API version or for per-modality endpoints. Model calls fail with "Azure OpenAI API version not found" unless the API version is provided another way: set `AZURE_OPENAI_API_VERSION` in the container environment, or create the credential through the API (`POST /api/credentials` accepts `api_version`, `endpoint_llm`, `endpoint_embedding`, `endpoint_stt` and `endpoint_tts`). Credentials migrated from environment variables carry these values over.

---

## Choosing a setup

- **Simplest:** OpenAI alone covers chat, embeddings, podcasts and transcription.
- **Many models, one bill:** OpenRouter, plus an embedding provider if you prefer a dedicated one.
- **Fully local:** Ollama (or LM Studio, oMLX) for chat and embeddings, and [Speaches](local-tts.md) for speech.
- **Language-only provider** (Anthropic, DeepSeek, DashScope, Novita, SiliconFlow, Z.ai): add Voyage AI, OpenAI, Google, Mistral or Ollama for embeddings, and a speech provider for podcasts.

---

## Legacy: Environment Variables (Deprecated)

Provider keys in environment variables (`OPENAI_API_KEY` and so on) still work as a fallback: the database is checked first, then the environment. They are deprecated and may stop working. If any are set, **Manage → Models** shows **Environment Variables Detected** with a **Migrate to Database** button that copies them into configurations. Which variables are copied is listed in the [Environment Reference](environment-reference.md#legacy-ai-provider-variables-deprecated).

---

## Related

- [API Configuration](../3-USER-GUIDE/api-configuration.md) — credentials in **Manage → Models** in detail
- [Environment Reference](environment-reference.md) — all variables
- [Ollama](ollama.md), [oMLX](omlx.md), [OpenAI-Compatible](openai-compatible.md), [Local speech](local-tts.md)
- [AI & Chat Issues](../6-TROUBLESHOOTING/ai-chat-issues.md) — when provider calls fail
