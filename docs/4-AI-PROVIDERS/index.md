# AI Providers

Open Notebook talks to AI models through providers. You connect a provider once in **Manage → Models**, pick which of its models to use, and choose a default model for each job (chat, embeddings, transcription and more).

This page has three parts:

1. [Connect a provider](#connect-a-provider): the steps every install guide links to
2. [Supported providers](#supported-providers): what each provider can do
3. [Choosing providers](#choosing-providers): which combination fits your setup

Per-provider details (where to get a key, base URLs, regional endpoints) are in the [AI Providers Configuration Guide](../5-CONFIGURATION/ai-providers.md).

---

## Connect a provider

Do this after Open Notebook is running and you can open the UI. It ends with a working chat.

> **Before you start:** `OPEN_NOTEBOOK_ENCRYPTION_KEY` must be set (every install guide sets it). If it isn't, the Models page shows "Encryption key not configured" and won't store keys.

### 1. Add a configuration

1. In the left sidebar, under **Manage**, click **Models**.
2. Find your provider in the list and click **Add Configuration**.
3. Fill in the form:
   - **Configuration Name**: any label, for example `Personal`.
   - **API Key**: the key from your provider. Local providers such as Ollama and oMLX don't need one (the field is marked optional).
   - **Base URL**: leave empty for cloud providers. Local and self-hosted providers need it (for example `http://ollama:11434` for the Ollama container).
   - **Google Vertex AI** uses a different form: **GCP Project ID** and **Region** (required) and an optional **Service Account JSON Path** instead of an API key. Without the JSON path, the server's default Google Cloud credentials are used.
4. Click **Add Configuration**.

### 2. Test the connection

On the new configuration, click **Test** (tooltip: *Test Connection*). A green check means Open Notebook reached the provider with your key. A red cross means the key, the base URL or the network is wrong; see [Troubleshooting](#troubleshooting).

### 3. Add models

1. On the same configuration, click **Models** (tooltip: *Sync Models*). The **Discover Models** dialog lists the models the provider offers.
2. Set **Model Type** first: `Language`, `Embedding`, `TTS` or `STT`. The list isn't filtered by type, so pick the type, then tick only models of that type.
3. Tick the models you want (or type a name in the search box to add one that isn't listed) and click **Add (N)**.
4. Open the dialog again for each other type you need. At minimum add one **Language** model and one **Embedding** model.

### 4. Set default models

Scroll down to **Default Model Assignments** on the same page.

- While a required default is missing, a notice lists it with an **Auto-assign Defaults** button. Click it to fill **Chat Model** and **Embedding Model** from the models you added.
- Or pick each default from its dropdown. Changes save immediately.

| Default | Required | Used for |
|---|---|---|
| **Chat Model** | Yes | Notebook and source chat |
| **Embedding Model** | Yes | Vector search and Ask |
| **Text-to-Speech Model** | No | Not used yet: podcasts use the voice model set in each speaker profile |
| **Speech-to-Text Model** | No | Transcribing audio and video sources |
| **Transformation Model** | No (uses the chat model) | Transformations and insights |
| **Tools Model** | No (uses the chat model) | Ask requests made through the API without explicit models (the Ask page uses the models picked there, which default to the chat model) |
| **Large Context Model** | No (uses the chat model) | Any prompt over ~105K tokens is sent here automatically |

**Auto-assign Defaults** only fills Chat Model and Embedding Model. Set Speech-to-Text by hand if you want audio/video transcription; for podcasts, pick a voice model in each speaker profile (**Podcasts → Profiles**).

### 5. Check that chat works

1. In the sidebar, click **Notebooks** → **New Notebook**, enter a name and click **Create New Notebook**.
2. In the notebook, click the **Add Source** button and pick **Add Source** from its menu (the other entry, **Add Existing Sources**, reuses sources you already have). Choose **Enter Text**, paste a paragraph, give it a title, then click **Next** through the remaining steps and **Done**.
3. Wait for the source to finish processing, then type a question in the chat panel and send it with **Ctrl+Enter** (**⌘+Enter** on macOS).

If you get an answer, you're done. Add more providers the same way at any time; each one gets its own configurations and models.

### Troubleshooting

- **Test fails on a cloud provider**: check the key on the provider's website and that the account has credit. Edit the configuration to replace the key.
- **Test fails on a local provider**: the base URL must be reachable *from the Open Notebook container*, not from your browser. `localhost` inside the container is the container itself. See [Ollama](../5-CONFIGURATION/ollama.md).
- **Chat says "No model configured…"**: a default is empty. Go back to step 4.
- **Source stays queued forever**: the background worker isn't running. In Docker it runs inside the `open_notebook` container (check `docker compose logs open_notebook`); from source you start it yourself.
- **"Decryption Error" on a configuration**: `OPEN_NOTEBOOK_ENCRYPTION_KEY` changed since the key was saved. Delete the configuration and add it again.
- More: [AI & Chat Issues](../6-TROUBLESHOOTING/ai-chat-issues.md).

---

## Supported providers

Open Notebook supports 24 providers. The table lists the model types each provider offers when you add a configuration. What you can actually add depends on the models in your provider account.

| Provider | Language | Embedding | Speech-to-Text | Text-to-Speech | Setup |
|---|:-:|:-:|:-:|:-:|---|
| OpenAI | ✅ | ✅ | ✅ | ✅ | [guide](../5-CONFIGURATION/ai-providers.md#openai) |
| Anthropic | ✅ | | | | [guide](../5-CONFIGURATION/ai-providers.md#anthropic-claude) |
| Google AI (Gemini) | ✅ | ✅ | ✅ | ✅ | [guide](../5-CONFIGURATION/ai-providers.md#google-gemini) |
| Groq | ✅ | | ✅ | | [guide](../5-CONFIGURATION/ai-providers.md#groq) |
| Mistral AI | ✅ | ✅ | ✅ | ✅ | |
| DeepSeek | ✅ | | | | |
| xAI (Grok) | ✅ | | | ✅ | |
| OpenRouter | ✅ | ✅ | ✅ | ✅ | [guide](../5-CONFIGURATION/ai-providers.md#openrouter) |
| DashScope (Qwen) | ✅ | | | | [guide](../5-CONFIGURATION/ai-providers.md#dashscope-qwen) |
| MiniMax | ✅ | | | ✅ | [guide](../5-CONFIGURATION/ai-providers.md#minimax) |
| Novita | ✅ | | | | [guide](../5-CONFIGURATION/ai-providers.md#novita) |
| SiliconFlow | ✅ | | | | [guide](../5-CONFIGURATION/ai-providers.md#siliconflow) |
| Z.ai | ✅ | | | | [guide](../5-CONFIGURATION/ai-providers.md#zai) |
| PayPerQ (PPQ) | ✅ | ✅ | ✅ | ✅ | [guide](../5-CONFIGURATION/ai-providers.md#payperq-ppq) |
| Cohere | ✅ | ✅ | | | [guide](../5-CONFIGURATION/ai-providers.md#cohere) |
| Voyage AI | | ✅ | | | |
| ElevenLabs | | | ✅ | ✅ | |
| Deepgram | | | ✅ | ✅ | |
| Ollama (local) | ✅ | ✅ | | | [guide](../5-CONFIGURATION/ollama.md) |
| oMLX (local, Apple Silicon) | ✅ | ✅ | | | [guide](../5-CONFIGURATION/omlx.md) |
| Azure OpenAI | ✅ | ✅ | ✅ | ✅ | [guide](../5-CONFIGURATION/ai-providers.md#azure-openai) |
| Google Vertex AI | ✅ | ✅ | | ✅ | |
| OpenAI Compatible | ✅ | ✅ | ✅ | ✅ | [guide](../5-CONFIGURATION/openai-compatible.md) |
| Anthropic Compatible | ✅ | | | | [guide](../5-CONFIGURATION/ai-providers.md#anthropic-compatible) |

**OpenAI Compatible** covers any server that speaks the OpenAI API: LM Studio, vLLM, LocalAI, and self-hosted speech servers ([local TTS](../5-CONFIGURATION/local-tts.md), [local STT](../5-CONFIGURATION/local-stt.md)). LM Studio has no provider of its own; add it as OpenAI Compatible.

---

## Choosing providers

Open Notebook needs at least a **language** model (for chat) and an **embedding** model (for search and Ask). Podcasts also need **text-to-speech**.

**One provider for everything.** OpenAI, Google AI, Mistral AI, OpenRouter, PayPerQ and Azure OpenAI offer all four model types under one key. This is the simplest setup.

**Language-only providers need a partner.** Anthropic, DeepSeek, DashScope, Novita, SiliconFlow, Z.ai and Anthropic Compatible offer only language models. Add a second provider for embeddings (and for text-to-speech if you want podcasts), for example OpenAI, Google AI, Mistral AI, Voyage AI or a local Ollama.

**Fully local.** Ollama and oMLX provide language and embedding models on your own hardware. For podcasts and transcription without the cloud, add a local speech server through OpenAI Compatible ([local TTS](../5-CONFIGURATION/local-tts.md), [local STT](../5-CONFIGURATION/local-stt.md)). Local models are slower on CPU; a GPU or Apple Silicon helps.

**Mixing is normal.** Each default model can come from a different provider, for example a cloud chat model with local embeddings.

**Changing the embedding model later** means rebuilding existing embeddings. The UI asks before switching and links to the rebuild on the **Advanced** page.

Prices, context windows and model line-ups change often, so this guide doesn't list them. Check each provider's own pricing and model pages.

---

## Next steps

- [AI Providers Configuration Guide](../5-CONFIGURATION/ai-providers.md): per-provider keys, base URLs and regional endpoints
- [Ollama](../5-CONFIGURATION/ollama.md): local models, networking and timeouts
- [User Guide](../3-USER-GUIDE/index.md): adding sources, chat, podcasts

**Need help?** Join the [Discord community](https://discord.gg/37XJPXfz2w).
