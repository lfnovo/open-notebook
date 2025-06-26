# AI Model Selection Guide

This guide helps you choose the best AI models for your Open Notebook setup. We'll cover what makes each provider special, which models work best for different tasks, and give you ready-to-use combinations to get started quickly.

## Understanding Model Types

Open Notebook uses four types of AI models:

- **Language Models**: For chat, text generation, summaries, and tool calling
- **Embedding Models**: For semantic search and content similarity
- **Text-to-Speech (TTS)**: For generating podcasts and audio content
- **Speech-to-Text (STT)**: For transcribing audio files

## What to Consider When Choosing Models

**💰 Cost**: Some models are free (Ollama), others charge per token
**🎯 Quality**: Higher quality models often cost more but produce better results
**⚡ Speed**: Smaller models are faster but may be less capable
**🔧 Features**: Some models excel at specific tasks like tool calling or large contexts
**🧠 Reasoning**: Newer reasoning models can show their thought process for transparent decision-making

---

## Provider Breakdown

### 🟦 Google (Gemini)
**Best for**: Large context processing, affordable high-quality models

**Language Models**
- `gemini-2.0-flash` - Excellent balance of price and performance with 1M context window
- `gemini-2.5-pro-preview-06-05` - Premium model for complex reasoning tasks

**Text-to-Speech**
- `gemini-2.5-flash-preview-tts` - Good quality at $10 per 1M tokens
- `gemini-2.5-pro-preview-tts` - Higher quality at $20 per 1M tokens

**Embedding**
- `text-embedding-004` - Solid performance with generous free tier

---

### 🟢 OpenAI
**Best for**: Reliable performance, excellent tool calling, wide ecosystem support

**Language Models**
- `gpt-4o-mini` - Great value for most tasks, perfect for everyday use
- `gpt-4o` - Premium quality with excellent tool calling capabilities

**Text-to-Speech**
- `tts-1` - Good quality for personal use and podcasts

**Speech-to-Text**
- `whisper-1` - Industry-standard transcription quality

**Embedding**
- `text-embedding-3-small` - Affordable at $0.02 per 1M tokens with solid performance

---

### 🎤 ElevenLabs
**Best for**: High-quality voice synthesis and transcription

**Text-to-Speech**
- `eleven_turbo_v2_5` - Excellent voice quality with reasonable pricing

**Speech-to-Text**
- `scribe_v1` - High-quality transcription service

---

### 🔵 DeepSeek
**Best for**: Cost-effective language models with good performance and advanced reasoning

**Language Models**
- `deepseek-chat` - Excellent quality-to-price ratio with 64k context window
- `deepseek-reasoner` - Advanced reasoning model that shows its thinking process (available via Ollama)

---

### 🟡 Mistral
**Best for**: European-based alternative with competitive pricing and reasoning capabilities

**Language Models**
- `mistral-medium-latest` - Good balance of quality and price
- `ministral-8b-latest` - Perfect for simple tasks like transformations
- `magistral` - Reasoning model with transparent thinking process

**Embedding**
- `mistral-embed` - Good quality, though not the most cost-effective

---

### ⚡ Grok (xAI)
**Best for**: Cutting-edge intelligence and reasoning

**Language Models**
- `grok-3` - Top-tier intelligence, premium pricing
- `grok-3-mini` - Excellent performance at more accessible pricing

---

### 🚢 Voyage AI
**Best for**: Specialized embedding models

**Embedding**
- `voyage-3.5-lite` - Competitive with OpenAI's offering at similar pricing

---

### 🟣 Anthropic (Claude)
**Best for**: High-quality reasoning and safety

**Language Models**
- `claude-3-5-sonnet-latest` - Exceptional quality for complex tasks

---

### 🦙 Ollama (Local/Free)
**Best for**: Privacy, offline use, and zero ongoing costs

**Language Models**
- `qwen3` - Excellent free alternative for most language tasks with reasoning capabilities
- `gemma3` - Great for chat and simple transformations
- `phi4` - Compact but capable model
- `deepseek-r1` - Advanced reasoning capabilities with transparent thinking
- `llama4` - Well-rounded performance
- `magistral` - Light-weight reasoning model


**Embedding**
- `mxbai-embed-large` - Outstanding free embedding model

---

## 🧠 Reasoning Models Support

Open Notebook fully supports **reasoning models** that show their thought process. These models output their internal reasoning within `<think>` tags, which Open Notebook automatically handles:

### How It Works
- **In Chat**: Reasoning content appears in a collapsible "🤔 AI Reasoning" section
- **In Transformations**: Clean output is stored while reasoning is filtered out
- **In Search**: Final answers are clean and focused

### Tested Models
We've tested extensively with these reasoning models:

- **DeepSeek-R1** (via Ollama) - Exceptional reasoning quality, completely free
- **Qwen3** (via Ollama) - Good reasoning capabilities with fast performance
- **Magistral** (via Mistral) - European alternative with solid reasoning

### Benefits
- **Transparency**: See exactly how the AI reached its conclusions
- **Trust**: Understand the reasoning behind responses
- **Learning**: Gain insights into AI problem-solving approaches
- **Clean Output**: Stored content remains focused and professional

### Getting Started
1. Install any reasoning model (we recommend starting with `deepseek-r1` via Ollama)
2. Use it like any other model - the reasoning interface appears automatically
3. Click the "🤔 AI Reasoning" expander to explore the AI's thought process

---

## Recommended Combinations

### 🌟 Best Value (Mixed Providers)
Perfect balance of cost and performance
- **Chat**: `gpt-4o-mini` (OpenAI) - Reliable and affordable
- **Tools**: `gpt-4o` (OpenAI) - Excellent tool calling
- **Transformations**: `ministral-8b-latest` (Mistral) - Cost-effective
- **Large Context**: `gemini-2.0-flash` (Google) - 1M context window
- **Embedding**: `text-embedding-3-small` (OpenAI) - Good price/performance
- **TTS**: `gemini-2.5-flash-preview-tts` (Google) - Affordable quality
- **STT**: `whisper-1` (OpenAI) - Industry standard

### 💰 Budget-Friendly (Mostly Free)
Great for getting started or keeping costs low
- **Language**: `qwen3` (Ollama) - Free and capable
- **Tools**: `qwen3` (Ollama) - Handles basic tool calling
- **Transformations**: `gemma3` (Ollama) - Free and fast
- **Embedding**: `mxbai-embed-large` (Ollama) - Free, high quality
- **TTS**: `gpt-4o-mini-tts` (OpenAI) - Reasonable cost
- **STT**: `whisper-1` (OpenAI) - Best value

### 🚀 High Performance (Premium)
When quality is your top priority
- **Chat**: `claude-3-5-sonnet-latest` (Anthropic) or `grok-3` (xAI) - Exceptional reasoning
- **Tools**: `gpt-4o` (OpenAI) or `claude-3-5-sonnet-latest` (Anthropic) or `grok-3` (xAI) - Best tool calling
- **Transformations**: `grok-3-mini` (xAI) - Smart and efficient
- **Large Context**: `gemini-2.5-pro-preview-06-05` (Google) - Premium quality
- **Embedding**: `voyage-3.5-lite` (Voyage) - Specialized performance
- **TTS**: `eleven_turbo_v2_5` (ElevenLabs) - Premium voice quality
- **STT**: `whisper-1` (OpenAI) - Proven reliability

### 🏢 Single Provider (OpenAI)
Simplify billing and setup with one provider
- **Chat**: `gpt-4o-mini` - Everyday conversations
- **Tools**: `gpt-4o` - Complex operations
- **Transformations**: `gpt-4o-mini` - Cost-effective processing
- **Embedding**: `text-embedding-3-small` - Solid performance
- **TTS**: `gpt-4o-mini-tts` - Great quality
- **STT**: `whisper-1` - Industry standard

## Setting up Models

Here are the environment variables that you need to set up for each provider:

| Provider | Environment Variables |
|----------|----------------------|
| Mistral | `MISTRAL_API_KEY` |
| Deepseek | `DEEPSEEK_API_KEY` |
| OpenAI | `OPENAI_API_KEY` |
| Google (Gemini) | `GEMINI_API_KEY` |
| X.AI | `XAI_API_KEY` |
| ElevenLabs | `ELEVENLABS_API_KEY` |
| Anthropic | `ANTHROPIC_API_KEY` |
| Ollama | `OLLAMA_BASE_URL` |
| Azure OpenAI | `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_API_VERSION`, `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_DEPLOYMENT_NAME` |
| Groq | `GROQ_API_KEY` |
| Vertex AI | `VERTEX_PROJECT`, `GOOGLE_APPLICATION_CREDENTIALS`, `VERTEX_LOCATION` |
| VOYAGE AI | `VOYAGE_API_KEY` |

## Tips to use Text to Speech

### OpenAI
To use the OpenAI provider for audio: 
1. Use "gpt-4o-mini-tts" as the audio model name
2. pass the following Environment Variables
    - OPENAI_API_KEY=your-openai-api-key

### Gemini
To use the Gemini provider for audio: 
1. Use "default" as the audio model name (since vertex does not require a model name)
2. pass the following Environment Variables
    - GEMINI_API_KEY=gemini-2.5-flash-preview-tts

### Google Cloud  / Vertex (previously supported as Google)

**If you were using this before, we recommend moving to GEMINI for better quality, price and ease of configuration.**

To use the Google Cloud (Vertex) provider for audio: 
1. Use "default" as the audio model name (since vertex does not require a model name)
2. pass the following Environment Variables
    - VERTEX_PROJECT=your-google-cloud-project-name
    - GOOGLE_APPLICATION_CREDENTIALS=./google-credentials.json
    - VERTEX_LOCATION=your-google-cloud-project-location
3. Setup the correct permissions in the [Google Cloud Console](https://github.com/souzatharsis/podcastfy/blob/main/usage/config.md)