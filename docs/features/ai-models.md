# AI Models & Providers

Open Notebook supports 16+ AI providers, giving you complete flexibility in choosing the AI models that best fit your needs, budget, and privacy requirements. This comprehensive guide covers everything you need to know about selecting, configuring, and optimizing your AI models.

## Quick Start

For immediate setup, use one of these configurations:

### OpenAI Only (Simplest)
```bash
# Set environment variable
export OPENAI_API_KEY=your_key_here

# Configure these models in Settings:
# Chat: gpt-5-mini
# Tools: gpt-5  
# Transformations: gpt-5-mini
# Embedding: text-embedding-3-small
# Speech-to-Text: whisper-1
# Text-to-Speech: tts-1
```

### Mixed Providers (Best Value)
```bash
# Environment variables
export OPENAI_API_KEY=your_key
export GEMINI_API_KEY=your_key
export OLLAMA_API_BASE=http://localhost:11434

# Recommended configuration in settings covered below
```

## Understanding Model Types

Open Notebook uses four distinct types of AI models, each optimized for specific tasks:

### 🧠 Language Models
- **Purpose**: Chat conversations, text generation, summaries, and tool calling
- **Key Features**: Reasoning, instruction following, context understanding
- **Usage**: Primary interface for AI interactions

### 🔍 Embedding Models  
- **Purpose**: Semantic search and content similarity matching
- **Key Features**: Convert text to numerical vectors for similarity comparison
- **Usage**: Power the search functionality across your content

### 🎙️ Text-to-Speech (TTS)
- **Purpose**: Generate podcasts and audio content
- **Key Features**: Natural-sounding voice synthesis
- **Usage**: Convert your notes and research into professional podcasts

### 🎧 Speech-to-Text (STT)
- **Purpose**: Transcribe audio and video files
- **Key Features**: Accurate transcription with speaker identification
- **Usage**: Convert audio/video sources into searchable text

## Provider Support Matrix

| Provider     | Language | Embedding | STT | TTS |
|--------------|----------|-----------|-----|-----|
| **OpenAI**       | ✅       | ✅        | ✅  | ✅  |
| **Anthropic**    | ✅       | ❌        | ❌  | ❌  |
| **Google (Gemini)** | ✅       | ✅        | ❌  | ✅  |
| **Ollama**       | ✅       | ✅        | ❌  | ❌  |
| **ElevenLabs**   | ❌       | ❌        | ✅  | ✅  |
| **Mistral**      | ✅       | ✅        | ❌  | ❌  |
| **DeepSeek**     | ✅       | ❌        | ❌  | ❌  |
| **xAI (Grok)**   | ✅       | ❌        | ❌  | ❌  |
| **Voyage AI**    | ❌       | ✅        | ❌  | ❌  |
| **Groq**         | ✅       | ❌        | ✅  | ❌  |
| **Vertex AI**    | ✅       | ✅        | ❌  | ✅  |
| **Azure OpenAI** | ✅       | ✅        | ✅  | ✅  |
| **OpenRouter**   | ✅       | ❌        | ❌  | ❌  |
| **Perplexity**   | ✅       | ❌        | ❌  | ❌  |
| **OpenAI Compatible** | ✅       | ✅        | ✅  | ✅  |

## Model Selection Guide

### 🎯 Selection Criteria

**💰 Cost Considerations**
- **Free**: Ollama models (run locally)
- **Budget**: OpenAI gpt-5-mini, Gemini Flash models
- **Premium**: Claude 3.5 Sonnet, gpt-5, Grok-3

**🎯 Quality Factors**
- **Reasoning**: Claude 3.5 Sonnet, Grok-3, DeepSeek-R1
- **Tool Calling**: gpt-5, Claude 3.5 Sonnet, Grok-3
- **Large Context**: Gemini models (up to 2M tokens)
- **Speed**: Groq models, Ollama local models

**🔧 Special Features**
- **Reasoning Models**: Show transparent thinking process
- **Multilingual**: Gemini, Claude, GPT-4
- **Code Generation**: Claude 3.5 Sonnet, gpt-5
- **Creative Writing**: Claude, gpt-5, Grok

## Provider Deep Dive

### 🟦 Google (Gemini)
**Best for**: Large context processing, cost-effective high-quality models

**Environment Setup**
```bash
export GEMINI_API_KEY=your_api_key_here

# Optional: Override the default Gemini API endpoint
# Use this for Vertex AI, custom proxies, or alternative endpoints
# export GEMINI_API_BASE_URL=https://your-custom-endpoint.com
```

**Recommended Models**
- **Language**: `gemini-2.0-flash`, `gemini-2.5-pro-preview-06-05`
- **TTS**: `gemini-2.5-flash-preview-tts`, `gemini-2.5-pro-preview-tts`
- **Embedding**: `text-embedding-004`

**Strengths**
- Massive context windows (up to 2M tokens)
- Excellent price-to-performance ratio
- Strong multilingual capabilities
- Integrated TTS with good quality

**Considerations**
- No STT support
- Newer models may have limited availability

---

### 🟢 OpenAI
**Best for**: Reliable performance, excellent tool calling, comprehensive ecosystem

**Environment Setup**
```bash
export OPENAI_API_KEY=your_api_key_here
```

**Recommended Models**
- **Language**: `gpt-5-mini`, `gpt-5`
- **TTS**: `tts-1`, `gpt-4o-mini-tts`
- **STT**: `whisper-1`
- **Embedding**: `text-embedding-3-small`

**Strengths**
- Most mature ecosystem
- Excellent tool calling capabilities
- Industry-standard STT with Whisper
- Consistent performance across models

**Considerations**
- Higher costs for premium models
- Data privacy concerns for sensitive content

---

### 🟣 Anthropic (Claude)
**Best for**: High-quality reasoning, safety, and nuanced understanding

**Environment Setup**
```bash
export ANTHROPIC_API_KEY=your_api_key_here
```

**Recommended Models**
- **Language**: `claude-3-5-sonnet-latest`

**Strengths**
- Exceptional reasoning capabilities
- Strong safety and alignment
- Excellent for complex analysis
- Superior code generation

**Considerations**
- Only language models available
- Higher cost per token
- Need additional providers for other model types

---

### 🦙 Ollama (Local/Free)
**Best for**: Privacy, offline use, zero ongoing costs

**Environment Setup**
```bash
# Install Ollama locally
curl -fsSL https://ollama.ai/install.sh | sh

# Set API base (if running remotely)
export OLLAMA_API_BASE=http://localhost:11434
```

**Recommended Models**
- **Language**: `qwen3`, `gemma3`, `phi4`, `deepseek-r1`, `llama4`
- **Embedding**: `mxbai-embed-large`

**Strengths**
- Completely free after setup
- Full data privacy (local processing)
- No internet dependency
- Support for reasoning models

**Considerations**
- Requires local hardware resources
- Limited model variety compared to cloud providers
- No TTS/STT capabilities

> **📖 Need detailed Ollama setup help?** Check our comprehensive [Ollama Setup Guide](ollama.md) for network configuration, Docker deployment, troubleshooting, and optimization tips.

---

### 🎤 ElevenLabs
**Best for**: Premium voice synthesis and transcription

**Environment Setup**
```bash
export ELEVENLABS_API_KEY=your_api_key_here
```

**Recommended Models**
- **TTS**: `eleven_turbo_v2_5`, `eleven-monolingual-v1`
- **STT**: `scribe_v1`, `eleven-stt-v1`

**Strengths**
- Highest quality voice synthesis
- Excellent transcription accuracy
- Multiple voice options
- Good pricing for audio services

**Considerations**
- Audio-only provider
- Requires separate language/embedding providers

---

### 🔵 DeepSeek
**Best for**: Cost-effective language models with advanced reasoning

**Environment Setup**
```bash
export DEEPSEEK_API_KEY=your_api_key_here
```

**Recommended Models**
- **Language**: `deepseek-chat`, `deepseek-reasoner`

**Strengths**
- Excellent quality-to-price ratio
- Advanced reasoning capabilities
- Large context windows (64k+)
- Strong performance on technical tasks

**Considerations**
- Limited to language models only
- Relatively new provider

---

### 🟡 Mistral
**Best for**: European alternative with competitive pricing

**Environment Setup**
```bash
export MISTRAL_API_KEY=your_api_key_here
```

**Recommended Models**
- **Language**: `mistral-medium-latest`, `ministral-8b-latest`, `magistral`
- **Embedding**: `mistral-embed`

**Strengths**
- European data governance
- Competitive pricing
- Good reasoning capabilities
- Strong multilingual support

**Considerations**
- Limited model variety
- No TTS/STT capabilities

---

### ⚡ xAI (Grok)
**Best for**: Cutting-edge intelligence and unrestricted responses

**Environment Setup**
```bash
export XAI_API_KEY=your_api_key_here
```

**Recommended Models**
- **Language**: `grok-3`, `grok-3-mini`

**Strengths**
- State-of-the-art reasoning
- Less restrictive than other providers
- Excellent for creative and analytical tasks
- Real-time information access

**Considerations**
- Premium pricing
- Limited to language models
- Relatively new provider

---

### 🚢 Voyage AI
**Best for**: Specialized high-performance embeddings

**Environment Setup**
```bash
export VOYAGE_API_KEY=your_api_key_here
```

**Recommended Models**
- **Embedding**: `voyage-3.5-lite`

**Strengths**
- Specialized in embeddings
- Competitive performance
- Good pricing for embeddings

**Considerations**
- Embedding-only provider
- Requires other providers for language models

---

### 🔧 OpenAI Compatible (LM Studio & Others)
**Best for**: Using any OpenAI-compatible API endpoint for all AI modalities, including LM Studio

**Environment Setup**
```bash
# Generic configuration (applies to all modalities)
export OPENAI_COMPATIBLE_BASE_URL=http://localhost:1234/v1
# Optional - only if your endpoint requires authentication
export OPENAI_COMPATIBLE_API_KEY=your_key_here

# Mode-specific configuration (for different endpoints per modality)
export OPENAI_COMPATIBLE_BASE_URL_LLM=http://localhost:1234/v1
export OPENAI_COMPATIBLE_BASE_URL_EMBEDDING=http://localhost:8080/v1
export OPENAI_COMPATIBLE_BASE_URL_STT=http://localhost:9000/v1
export OPENAI_COMPATIBLE_BASE_URL_TTS=http://localhost:9000/v1
```

**Common Use Cases**
- **LM Studio**: Run models locally with a familiar UI
- **Text Generation WebUI**: Alternative local inference
- **vLLM**: High-performance inference server
- **Custom Endpoints**: Any OpenAI-compatible API

**Strengths**
- Use any OpenAI-compatible endpoint
- **NEW**: Full support for all 4 modalities (language, embeddings, STT, TTS)
- Configure different endpoints for different capabilities
- Perfect for LM Studio users
- Flexibility in model deployment
- Works with local and remote endpoints

**Considerations**
- Performance depends on your hardware (for local)
- Model availability varies by endpoint
- Some endpoints may not support all features

> **📖 Need detailed setup help?** Check our comprehensive [OpenAI-Compatible Setup Guide](openai-compatible.md) for LM Studio, Text Generation WebUI, vLLM, and other configurations.

---

### ☁️ Azure OpenAI
**Best for**: Enterprise deployments with Microsoft Azure infrastructure

**Environment Setup**
```bash
# Generic configuration (applies to all modalities)
export AZURE_OPENAI_API_KEY=your_key
export AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
export AZURE_OPENAI_API_VERSION=2024-12-01-preview

# Mode-specific configuration (for different deployments per modality)
# Use these when you have separate Azure deployments for different capabilities
export AZURE_OPENAI_API_KEY_LLM=your_llm_key
export AZURE_OPENAI_ENDPOINT_LLM=https://llm-resource.openai.azure.com/
export AZURE_OPENAI_API_VERSION_LLM=2024-12-01-preview

export AZURE_OPENAI_API_KEY_EMBEDDING=your_embedding_key
export AZURE_OPENAI_ENDPOINT_EMBEDDING=https://embedding-resource.openai.azure.com/
export AZURE_OPENAI_API_VERSION_EMBEDDING=2024-12-01-preview

# STT and TTS also supported with _STT and _TTS suffixes
```

**Recommended Models**
- **Language**: `gpt-4o`, `gpt-4o-mini`, `gpt-35-turbo`
- **Embedding**: `text-embedding-3-small`, `text-embedding-ada-002`
- **STT**: `whisper` (deployment name for Whisper model)
- **TTS**: `tts`, `tts-hd` (deployment names for TTS models)

**Strengths**
- Enterprise-grade security and compliance
- **NEW**: Full support for modality-specific deployments
- Configure different Azure resources for different capabilities
- Integration with Azure ecosystem
- SLA guarantees and dedicated support
- Regional deployment options

**Use Cases**
- **Single Deployment**: Use generic configuration when all models are in one Azure resource
- **Multi-Deployment**: Use mode-specific configuration for separate resources (e.g., production LLM in one region, embeddings in another)
- **Cost Optimization**: Different Azure subscriptions or resources for different workloads
- **Compliance**: Separate deployments for different data residency requirements

**Considerations**
- Requires Azure subscription and resource setup
- More complex configuration than standard OpenAI
- Limited to Azure OpenAI service capabilities
- Deployment-based model access (not all models available)

## 🧠 Reasoning Models

Open Notebook fully supports **reasoning models** that show their transparent thinking process. These models output their internal reasoning within `<think>` tags, which Open Notebook automatically handles.

### How Reasoning Models Work

**In Chat Interface**
- Reasoning content appears in a collapsible "🤔 AI Reasoning" section
- Clean final answers are displayed prominently
- Users can explore the AI's thought process

**In Transformations**
- Clean output is stored in your notes
- Reasoning is filtered out automatically
- Professional results without internal monologue

**In Search**
- Final answers remain clean and focused
- Reasoning helps improve answer quality

### Supported Reasoning Models

| Model | Provider | Access | Quality |
|-------|----------|---------|---------|
| **deepseek-r1** | Ollama | Free | Exceptional |
| **qwen3** | Ollama | Free | Very Good |
| **magistral** | Mistral | Paid | Good |
| **deepseek-reasoner** | DeepSeek | Paid | Excellent |

### Benefits of Reasoning Models

- **Transparency**: See exactly how AI reached conclusions
- **Trust**: Understand the logic behind responses
- **Learning**: Gain insights into AI problem-solving
- **Debugging**: Identify where AI reasoning went wrong
- **Quality**: Better answers through explicit reasoning

## Recommended Configurations

### 🌟 Best Value (Mixed Providers)
*Perfect balance of cost and performance*

```bash
# Environment Variables
export OPENAI_API_KEY=your_key
export GEMINI_API_KEY=your_key
export OLLAMA_API_BASE=http://localhost:11434
```

| Model Default | Recommended Model | Provider |
|---------------|-------------------|----------|
| Chat Model | `gpt-5-mini` | OpenAI |
| Tools Model | `gpt-5` | OpenAI |
| Transformations | `ministral-8b-latest` | Mistral |
| Large Context | `gemini-2.0-flash` | Google |
| Embedding | `text-embedding-3-small` | OpenAI |
| Text-to-Speech | `gemini-2.5-flash-preview-tts` | Google |
| Speech-to-Text | `whisper-1` | OpenAI |

**Monthly Cost Estimate**: $20-50 for moderate usage

---

### 💰 Budget-Friendly (Mostly Free)
*Great for getting started or keeping costs low*

```bash
# Environment Variables
export OPENAI_API_KEY=your_key  # For STT/TTS only
export OLLAMA_API_BASE=http://localhost:11434
```

| Model Default | Recommended Model | Provider |
|---------------|-------------------|----------|
| Chat Model | `qwen3` | Ollama |
| Tools Model | `qwen3` | Ollama |
| Transformations | `gemma3` | Ollama |
| Large Context | `qwen3` | Ollama |
| Embedding | `mxbai-embed-large` | Ollama |
| Text-to-Speech | `gpt-4o-mini-tts` | OpenAI |
| Speech-to-Text | `whisper-1` | OpenAI |

**Monthly Cost Estimate**: $5-15 (only for audio services)

---

### 🚀 High Performance (Premium)
*When quality is your top priority*

```bash
# Environment Variables
export ANTHROPIC_API_KEY=your_key
export XAI_API_KEY=your_key
export GEMINI_API_KEY=your_key
export VOYAGE_API_KEY=your_key
export ELEVENLABS_API_KEY=your_key
export OPENAI_API_KEY=your_key
```

| Model Default | Recommended Model | Provider |
|---------------|-------------------|----------|
| Chat Model | `claude-3-5-sonnet-latest` | Anthropic |
| Tools Model | `grok-3` | xAI |
| Transformations | `grok-3-mini` | xAI |
| Large Context | `gemini-2.5-pro-preview-06-05` | Google |
| Embedding | `voyage-3.5-lite` | Voyage |
| Text-to-Speech | `eleven_turbo_v2_5` | ElevenLabs |
| Speech-to-Text | `whisper-1` | OpenAI |

**Monthly Cost Estimate**: $100-300 for moderate usage

---

### 🏢 Single Provider (OpenAI)
*Simplify billing and setup*

```bash
# Environment Variables
export OPENAI_API_KEY=your_key
```

| Model Default | Recommended Model | Provider |
|---------------|-------------------|----------|
| Chat Model | `gpt-5-mini` | OpenAI |
| Tools Model | `gpt-5` | OpenAI |
| Transformations | `gpt-5-mini` | OpenAI |
| Large Context | `gpt-5` | OpenAI |
| Embedding | `text-embedding-3-small` | OpenAI |
| Text-to-Speech | `gpt-4o-mini-tts` | OpenAI |
| Speech-to-Text | `whisper-1` | OpenAI |

**Monthly Cost Estimate**: $30-80 for moderate usage

## Setup Instructions

### 1. Environment Variables

Set up your API keys using environment variables. Here's the complete list:

```bash
# Core Providers
export OPENAI_API_KEY=your_key
export ANTHROPIC_API_KEY=your_key
export GEMINI_API_KEY=your_key
export GEMINI_API_BASE_URL=https://custom-endpoint.com  # Optional

# Additional Language Providers
export MISTRAL_API_KEY=your_key
export DEEPSEEK_API_KEY=your_key
export XAI_API_KEY=your_key
export GROQ_API_KEY=your_key
export OPENROUTER_API_KEY=your_key

# Audio Providers
export ELEVENLABS_API_KEY=your_key

# Embedding Providers
export VOYAGE_API_KEY=your_key

# Local/Cloud Infrastructure
export OLLAMA_API_BASE=http://localhost:11434

# Azure OpenAI
# Generic configuration (applies to all modalities)
export AZURE_OPENAI_API_KEY=your_key
export AZURE_OPENAI_ENDPOINT=your_endpoint
export AZURE_OPENAI_API_VERSION=2024-12-01-preview

# Mode-specific configuration (for different deployments per modality)
export AZURE_OPENAI_API_KEY_LLM=your_llm_key
export AZURE_OPENAI_ENDPOINT_LLM=your_llm_endpoint
export AZURE_OPENAI_API_VERSION_LLM=2024-12-01-preview

export AZURE_OPENAI_API_KEY_EMBEDDING=your_embedding_key
export AZURE_OPENAI_ENDPOINT_EMBEDDING=your_embedding_endpoint
export AZURE_OPENAI_API_VERSION_EMBEDDING=2024-12-01-preview
# Similarly for _STT and _TTS

# Vertex AI
export VERTEX_PROJECT=your_project
export GOOGLE_APPLICATION_CREDENTIALS=./google-credentials.json
export VERTEX_LOCATION=us-east5

# OpenAI Compatible (LM Studio, etc.)
export OPENAI_COMPATIBLE_BASE_URL=http://localhost:1234/v1
export OPENAI_COMPATIBLE_API_KEY=your_key  # Optional
```

### 2. Using Docker

For Docker deployments, pass environment variables:

```bash
docker run -d \
  --name open-notebook \
  -p 8502:8502 -p 5055:5055 \
  -v ./notebook_data:/app/data \
  -v ./surreal_single_data:/mydata \
  -e OPENAI_API_KEY=your_key \
  -e GEMINI_API_KEY=your_key \
  -e ANTHROPIC_API_KEY=your_key \
  lfnovo/open_notebook:v1-latest-single
```

### 3. Model Configuration

After setting environment variables:

1. **Access Settings**: Go to the Settings page in Open Notebook
2. **Create Models**: Add your models for each provider
3. **Set Defaults**: Configure default models for each task type
4. **Test Models**: Use the Playground to test model performance

### 4. Provider-Specific Setup

#### OpenAI
```bash
export OPENAI_API_KEY=sk-your-key-here
```
- Get your API key from [OpenAI Platform](https://platform.openai.com/api-keys)
- Supports all model types
- Immediate activation

#### Anthropic
```bash
export ANTHROPIC_API_KEY=sk-ant-your-key-here
```
- Get your API key from [Anthropic Console](https://console.anthropic.com/)
- Only language models available
- Requires separate providers for other types

#### Google (Gemini)
```bash
export GEMINI_API_KEY=your-key-here

# Optional: Custom API endpoint (for Vertex AI, proxies, etc.)
# export GEMINI_API_BASE_URL=https://your-custom-endpoint.com
```
- Get your API key from [Google AI Studio](https://makersuite.google.com/app/apikey)
- Excellent for large context and TTS
- Cost-effective option
- Supports custom endpoints via `GEMINI_API_BASE_URL` for advanced deployments

#### Ollama (Local)
```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Pull models
ollama pull qwen3
ollama pull mxbai-embed-large

# Set API base if remote
export OLLAMA_API_BASE=http://your-server:11434
```

#### ElevenLabs
```bash
export ELEVENLABS_API_KEY=your-key-here
```
- Get your API key from [ElevenLabs](https://elevenlabs.io/)
- Premium voice synthesis
- Excellent for podcast generation

## Advanced Configuration

### Model Switching

You can switch models at runtime:

**In Chat**
- Use the model selector dropdown
- Changes apply to current conversation

**In Transformations**
- Configure per-transformation defaults
- Override on individual operations

**In Settings**
- Change global defaults
- Affects all new operations

### Performance Optimization

**For Speed**
- Use smaller models for simple tasks
- Groq for fast inference
- Local Ollama models for instant response

**For Quality**
- Use premium models for complex reasoning
- Claude 3.5 Sonnet for analysis
- GPT-4o for tool calling

**For Cost**
- Use cheaper models for transformations
- Ollama for free processing
- OpenAI mini models for everyday use

### Context Management

**Small Context (< 32k tokens)**
- Any modern language model
- Faster processing
- Lower costs

**Medium Context (32k-128k tokens)**
- GPT-4o, Claude 3.5 Sonnet
- Good balance of speed and capacity

**Large Context (> 128k tokens)**
- Gemini models (up to 2M tokens)
- Essential for large document processing
- Higher costs but necessary for big content

## Cost Optimization Strategies

### 1. Tiered Model Strategy

Use different models for different complexity levels:

```
Simple Tasks (70% of usage):
- Chat: gpt-5-mini or qwen3 (Ollama)
- Transformations: ministral-8b-latest

Complex Tasks (25% of usage):
- Analysis: claude-3-5-sonnet-latest
- Tool calling: gpt-5

Specialized Tasks (5% of usage):
- Large context: gemini-2.0-flash
- Premium TTS: eleven_turbo_v2_5
```

### 2. Smart Model Selection

**For Transformations**
- Use smaller, cheaper models
- Batch multiple operations
- Cache results when possible

**For Chat**
- Start with mini models
- Escalate to premium for complex queries
- Use reasoning models for transparency

**For Embeddings**
- Use free Ollama models when possible
- OpenAI for balanced performance
- Voyage for specialized needs

### 3. Usage Monitoring

Track your usage patterns:

```bash
# Monitor API usage through provider dashboards
# Set up billing alerts
# Review monthly costs by model
# Optimize based on actual usage patterns
```

### 4. Free Tier Maximization

**Ollama (Completely Free)**
- Language models for most tasks
- Embeddings for search
- No usage limits after setup

**Free Tiers**
- OpenAI: $5 monthly credit for new users
- Anthropic: Limited free tier
- Google: Generous free tier for Gemini

### 5. Batch Processing

Process multiple items together:
- Combine similar transformations
- Use larger context windows efficiently
- Reduce API call overhead

## Troubleshooting

### Common Issues

**API Key Problems**
```bash
# Check environment variables
echo $OPENAI_API_KEY

# Verify key format
# OpenAI: sk-...
# Anthropic: sk-ant-...
# Google: starts with alphanumeric
```

**Model Not Found**
- Verify model name spelling
- Check provider availability
- Ensure API key has access to model

**Rate Limiting**
- Implement retry logic
- Use different models for different tasks
- Monitor API quotas

**High Costs**
- Review model usage patterns
- Switch to cheaper models for simple tasks
- Use free Ollama models where possible

### Provider-Specific Issues

**OpenAI**
- Rate limits: Upgrade to paid tier
- Model access: Check account tier
- Usage limits: Monitor dashboard

**Anthropic**
- Beta access: Some models require approval
- Rate limits: Request increase if needed
- Region restrictions: Check availability

**Google (Gemini)**
- Quota limits: Monitor usage
- Model availability: Some models are preview
- API key restrictions: Check project settings

**Ollama**
- Model download: Ensure sufficient disk space
- Performance: Check hardware requirements
- Network: Verify base URL configuration

### Performance Issues

**Slow Responses**
- Use smaller models
- Reduce context size
- Consider local Ollama models

**Poor Quality**
- Upgrade to premium models
- Improve prompting
- Use reasoning models for complex tasks

**High Latency**
- Check network connectivity
- Use geographically closer providers
- Consider local Ollama deployment

## Best Practices

### 1. Model Selection

**Match Models to Tasks**
- Simple chat: Mini models
- Complex analysis: Premium models
- Transformations: Efficient models
- Large documents: High-context models

**Consider Cost vs. Quality**
- Use premium models only when necessary
- Free models for development and testing
- Monitor and optimize usage patterns

### 2. Security & Privacy

**Sensitive Data**
- Use local Ollama models
- Avoid sending sensitive content to cloud providers
- Consider on-premises deployment

**API Key Management**
- Use environment variables
- Rotate keys regularly
- Monitor usage for anomalies

### 3. Reliability

**Fallback Strategies**
- Configure multiple providers
- Have backup models ready
- Implement retry logic

**Testing**
- Test new models in playground
- Validate performance before deployment
- Monitor quality metrics

### 4. Optimization

**Performance Tuning**
- Profile model performance
- Optimize context size
- Use appropriate model for each task

**Cost Management**
- Set up billing alerts
- Regular usage reviews
- Optimize model selection

## Getting Help

**Community Support**
- [Discord Server](https://discord.gg/37XJPXfz2w) - Get help from the community
- [GitHub Issues](https://github.com/lfnovo/open-notebook/issues) - Report bugs and request features

**Documentation**
- [User Guide](../user-guide/index.md) - Learn how to use Open Notebook
- [Getting Started](../getting-started/index.md) - Quick setup guide
- [Troubleshooting](../troubleshooting/index.md) - Solve common issues

**Testing Your Setup**
- Use the Playground in Settings to test models
- Try different model combinations
- Monitor performance and costs

This comprehensive guide should help you make informed decisions about AI models for your Open Notebook deployment. Start with a simple configuration and gradually optimize based on your specific needs and usage patterns.