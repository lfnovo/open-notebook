# Model Provider Support

Open Notebook supports multiple AI model providers, giving you flexibility in choosing the AI that best fits your needs. This page combines a high-level overview with detailed recommendations to help you pick the right models for your workflow.

## Understanding Model Types

Open Notebook uses four types of AI models:

- **Language Models**: For chat, text generation, summaries, and tool calling
- **Embedding Models**: For semantic search and content similarity
- **Text-to-Speech (TTS)**: For generating podcasts and audio content
- **Speech-to-Text (STT)**: For transcribing audio files

## What to Consider When Choosing Models

- **💰 Cost**: Some models are free (Ollama), others charge per token
- **🎯 Quality**: Higher quality models often cost more but produce better results
- **⚡ Speed**: Smaller models are faster but may be less capable
- **🔧 Features**: Some models excel at specific tasks like tool calling or large contexts

## Provider Highlights and Recommendations

| Provider     | Highlights & Best Use Cases                                                                                 |
|-------------|------------------------------------------------------------------------------------------------------------|
| **OpenAI**      | Reliable performance, excellent tool calling, wide ecosystem support. Recommended: `gpt-4o`, `gpt-4o-mini`, `whisper-1` (STT), `tts-1` (TTS), `text-embedding-3-small` (Embedding) |
| **Anthropic**   | Exceptional reasoning, especially with Sonnet 3.5. Recommended: `claude-3-5-sonnet-latest` (Chat/Tools)  |
| **Gemini (Google)** | Large context (up to 2M tokens), affordable high-quality models. Recommended: `gemini-2.0-flash`, `gemini-2.5-pro-preview-06-05` (Language), `gemini-2.5-flash-preview-tts` (TTS), `text-embedding-004` (Embedding) |
| **Ollama**      | Free, local models. Great for experimentation and transformation tasks. Recommended: `gemma3`, `qwen3`, `phi4`, `deepseek-r1`, `llama4` (Language), `mxbai-embed-large` (Embedding) |
| **ElevenLabs**  | High-quality voice synthesis and transcription. Recommended: `eleven-monolingual-v1`, `eleven-multilingual-v2` (TTS), `eleven-stt-v1` (STT) |
| **Open Router** | Access to several open source models, Cohere, Mistral, xAI, etc.                                        |
| **Groq**        | Very fast inference, but limited model availability.                                                     |
| **xAI**         | Powerful Grok model, less guardrails, great responses. Recommended: `grok-3`, `grok-3-mini`             |
| **Vertex**      | For Google Cloud environments.                                                                          |
| **Voyage**      | Specialized embedding models. Recommended: `voyage-3.5-lite` (Embedding)                                |
| **Mistral**     | European-based, cost-effective, strong language and embedding models. Recommended: `mistral-medium-latest`, `ministral-8b-latest` (Language), `mistral-embed` (Embedding) |
| **Deepseek**    | Cost-effective language models. Recommended: `deepseek-chat` (Language)                                 |


---

### Provider-Specific Model Recommendations

**Google (Gemini):**
- Language: `gemini-2.0-flash`, `gemini-2.5-pro-preview-06-05`
- TTS: `gemini-2.5-flash-preview-tts`, `gemini-2.5-pro-preview-tts`
- Embedding: `text-embedding-004`

**OpenAI:**
- Language: `gpt-4o-mini`, `gpt-4o`
- TTS: `tts-1`, `gpt-4o-mini-tts`
- STT: `whisper-1`
- Embedding: `text-embedding-3-small`

**ElevenLabs:**
- TTS: `eleven-monolingual-v1`, `eleven-multilingual-v2`, `eleven_turbo_v2_5`
- STT: `eleven-stt-v1`, `scribe_v1`

**Anthropic:**
- Language: `claude-3-5-sonnet-latest`

**xAI:**
- Language: `grok-3`, `grok-3-mini`

**Ollama:**
- Language: `gemma3`, `qwen3`, `phi4`, `deepseek-r1`, `llama4`
- Embedding: `mxbai-embed-large`

**Voyage:**
- Embedding: `voyage-3.5-lite`

**Mistral:**
- Language: `mistral-medium-latest`, `ministral-8b-latest`
- Embedding: `mistral-embed`

**Deepseek:**
- Language: `deepseek-chat`

---

All providers are installed out of the box. All you need to do is to setup the environment variable configurations (API Keys, etc) for your selected provider and decide which models to use. 

Please refer to the [`.env.example`](https://github.com/lfnovo/open-notebook/blob/main/.env.example) file for instructions on which ENV variables are necessary for each. 


### Create models on the Settings page

Go to the settings page and create your different models.

> 📝 **Notice:** For complete usage of all the features, you need to setup at least 4 models (one of each type).

| Model Type        | Supported Providers                                                   |
|-------------------|-----------------------------------------------------------------------|
| Language          | OpenAI, Anthropic, Open Router, LiteLLM, Vertex AI, Gemini, Ollama, xAI, Groq, Mistral, Deepseek |
| Embedding         | OpenAI, Gemini, Vertex AI, Ollama, Mistral                                     |
| Speech to Text    | OpenAI, Groq, ElevenLabs                                              |
| Text to Speech    | OpenAI, ElevenLabs, Gemini, Vertex                                            |

If you are not sure which models to setup, the Model Settings page will offer some options for you to get started with.

After setting up the models, head to the Model Defaults tab to define the default models. There are several defaults to setup:

| Model Default      | Purpose                                      |
|--------------------|----------------------------------------------|
| Chat Model         | Will be used on all chats                     |
| Transformation Model | Will be used for summaries, insights, etc   |
| Large Context      | For content higher than 110k tokens (use Gemini here) |
| Speech to Text     | For transcribing text from your audio/video uploads |
| Text to Speech     | For generating podcasts                       |
| Embedding          | For creating vector representation of content |

All model types and defaults are required for now. If you are not sure which to pick, go with OpenAI, the only one that covers all possible model types.

The reason for opting for this route is because different LLMs will behave better/worse depending on the type of request and type of tools offered. So it makes sense to build a more refined system to decide which model should process which task.

For instance, you can use an Ollama-based model, like `gemma3`, to do summarization and document query, and use OpenAI/Claude for chat. The whole idea is to allow you to experiment on cost/performance.

## Suggested Model Combinations

Here are some ready-to-use combinations for different tasks:

- **Chat**: `claude-3-5-sonnet-latest` (Anthropic) or `grok-3` (xAI) - Exceptional reasoning
- **Tools**: `gpt-4o` (OpenAI) or `claude-3-5-sonnet-latest` (Anthropic) or `grok-3` (xAI) - Best tool calling
- **Transformations**: `grok-3-mini` (xAI) - Smart and efficient
- **Large Context**: `gemini-2.5-pro-preview-06-05` (Google) - Premium quality
- **Embedding**: `voyage-3.5-lite` (Voyage) - Specialized performance

We are working hard to support more providers and model types to give users more flexibility and options.

These are some suggested configurations for different use cases and budgets:

### Best in Class

| Model Default | Model Name |
|------------|-----------|
| Chat Model | claude-3-5-sonnet-latest |
| Transformation Model | gpt-4o-mini |
| Large Context | gemini-1.5-pro |
| Speech to Text | whisper-1 |
| Text to Speech | eleven_turbo_v2_5 (elevenlabs)  |
| Embedding | text-embedding-3-small |

### Open AI Only Configuration

| Model Default | Model Name |
|------------|-----------|
| Chat Model | gpt-4o-mini |
| Transformation Model | gpt-4o-mini |
| Large Context | gpt-4o-mini (you will be limited to 128k tokens) |
| Speech to Text | whisper-1 |
| Text to Speech | tts-1-hd  |
| Embedding | text-embedding-3-small |


### Gemini Only Configuration

| Model Default | Model Name |
|------------|-----------|
| Chat Model | gemini-1.5-flash |
| Transformation Model | gemini-1.5-flash |
| Large Context | gemini-1.5-pro |
| Speech to Text | (not available yet) |
| Text to Speech | default |
| Embedding | text-embedding-004 |

### Open Source Only (using Ollama)

| Model Default | Model Name |
|------------|-----------|
| Chat Model | qwen2.5 or gemma2 or phi3 or llama3.2 |
| Transformation Model |qwen2.5 or gemma2 or phi3 or llama3.2 |
| Large Context |qwen2.5 or gemma2 or phi3 or llama3.2 (limited to 128k) |
| Speech to Text | (not possible yet) |
| Text to Speech | (not possible yet)  |
| Embedding | mxbai-embed-large |

We are working hard to support more providers and model types to give users more flexibility and options.

## Testing your models

If you are not sure which model will work best for you, you can try them up on the Playground section and see for yourself how they handle different tasks.
