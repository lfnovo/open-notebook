# Open Notebook - Start Here

**Open Notebook** is a self-hosted, privacy-focused AI research assistant. Add documents, web pages, audio and video, chat with an AI about them with citations, take notes, and turn your research into podcasts, using the AI providers you choose.

## Choose your path

Each quick start installs Open Notebook with Docker Compose and ends with a working chat.

### I have an API key for a cloud AI provider
OpenAI, Anthropic, Google, Mistral, Groq, OpenRouter and more.

→ [Cloud Providers Quick Start](quick-start-cloud.md) (about 5 minutes)

### I want to run everything locally
Ollama in Docker next to Open Notebook. No API keys; nothing leaves your machine.

→ [Local Quick Start](quick-start-local.md) (about 10 minutes, plus model downloads)

**Already have Ollama installed on your computer?** → [External Ollama Quick Start](quick-start-external-ollama.md)

### Something else
Running from source, Windows without Docker, or a hosting platform → [Installation Guide](../1-INSTALLATION/index.md)

---

## What you can do

- **Add content**: PDFs, Office and OpenDocument files, web pages, YouTube, audio, video, plain text
- **Chat**: ask questions about the sources in a notebook, with citations, and choose what each source shares with the AI
- **Ask and search**: full-text and semantic search across everything
- **Transform**: run summaries and extraction prompts on sources to produce insights
- **Take notes**: write your own or save AI answers as notes
- **Create podcasts**: 1 to 4 speakers with configurable profiles

## Open Notebook and Google Notebook LM

| | Open Notebook | Google Notebook LM |
|---|---|---|
| **Where it runs** | Your machine or server | Google's cloud |
| **AI models** | 20+ providers, cloud or local | Google's models |
| **Podcast speakers** | 1–4, configurable profiles | Google's formats |
| **Cost** | Free software; you pay your AI provider (nothing with local models) | Free tier and subscriptions |
| **Offline** | Yes, with local models | No |

## Prerequisites

- **Docker** for the quick starts. [From source](../1-INSTALLATION/from-source.md) and [Windows native](../1-INSTALLATION/windows-native.md) installs don't need Docker for the app itself.
- **An AI provider**: a cloud API key, or a local model server such as Ollama.

---

**Need help?** Join our [Discord community](https://discord.gg/37XJPXfz2w) or see the [full documentation](../index.md).
