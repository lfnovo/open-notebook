# Installation Guide

Choose your installation route based on your setup and use case.

## Quick Decision: Which Route?

### 🚀 I want the easiest setup (Recommended for most)
**→ [Docker Compose](docker-compose.md)** - Multi-container setup, production-ready
- ✅ All features working
- ✅ Clear separation of services
- ✅ Easy to scale
- ✅ Works on Mac, Windows, Linux
- ⏱️ 5 minutes to running

---

### 🏠 I want everything in one container (Simplified)
**→ [Single Container](single-container.md)** - All-in-one for simple deployments
- ✅ Minimal configuration
- ✅ Lower resource usage
- ✅ Good for shared hosting
- ✅ Works on PikaPods, Railway, etc.
- ⏱️ 3 minutes to running

---

### 👨‍💻 I want to develop/contribute (Developers only)
**→ [From Source](from-source.md)** - Clone repo, set up locally
- ✅ Full control over code
- ✅ Easy to debug
- ✅ Can modify and test
- ⚠️ Requires Python 3.11+, Node.js
- ⏱️ 10 minutes to running

---


## System Requirements

### Minimum
- **RAM**: 4GB
- **Storage**: 2GB for app + space for documents
- **CPU**: Any modern processor
- **Network**: Internet (optional for offline setup)

### Recommended
- **RAM**: 8GB+
- **Storage**: 10GB+ for documents and models
- **CPU**: Multi-core processor
- **GPU**: Optional (speeds up local AI models)

---

## AI Provider Options

### Cloud-Based (Pay-as-you-go)
- **OpenAI** - GPT-4, GPT-4o, fast and capable
- **Anthropic (Claude)** - Claude 3.5 Sonnet, excellent reasoning
- **Google Gemini** - Multimodal, cost-effective
- **Groq** - Ultra-fast inference
- **Others**: Mistral, DeepSeek, xAI, OpenRouter

**Cost**: Usually $0.01-$0.10 per 1K tokens
**Speed**: Fast (sub-second)
**Privacy**: Your data sent to cloud

### Local (Free, Private)
- **Ollama** - Run open-source models locally
- **LM Studio** - Desktop app for local models
- **Hugging Face models** - Download and run

**Cost**: $0 (just electricity)
**Speed**: Depends on your hardware (slow to medium)
**Privacy**: 100% offline

---

## Choose a Route

**Already know which way to go?** Pick your installation path:

- [Docker Compose](docker-compose.md) - **Most users**
- [Single Container](single-container.md) - **Shared hosting**
- [From Source](from-source.md) - **Developers**

> **Privacy-first?** Any installation method works with Ollama for 100% local AI. See [Local Quick Start](../0-START-HERE/quick-start-local.md).

---

## Pre-Installation Checklist

Before installing, you'll need:

- [ ] **Docker** (for Docker routes) or **Node.js 18+** (for source)
- [ ] **AI Provider API key** (OpenAI, Anthropic, etc.) OR willingness to use free local models
- [ ] **At least 4GB RAM** available
- [ ] **Stable internet** (or offline setup with Ollama)

---

## Detailed Installation Instructions

### For Docker Users
1. Install [Docker Desktop](https://docker.com/products/docker-desktop)
2. Choose: [Docker Compose](docker-compose.md) or [Single Container](single-container.md)
3. Follow the step-by-step guide
4. Access at `http://localhost:8502`

### For Source Installation (Developers)
1. Have Python 3.11+, Node.js 18+, Git installed
2. Follow [From Source](from-source.md)
3. Run `make start-all`
4. Access at `http://localhost:8502` (frontend) or `http://localhost:5055` (API)

---

## After Installation

Once you're up and running:

1. **Configure Models** - Choose your AI provider in Settings
2. **Create First Notebook** - Start organizing research
3. **Add Sources** - PDFs, web links, documents
4. **Explore Features** - Chat, search, transformations
5. **Read Full Guide** - [User Guide](../3-USER-GUIDE/index.md)

---

## Troubleshooting During Installation

**Having issues?** Check the troubleshooting section in your chosen installation guide, or see [Quick Fixes](../6-TROUBLESHOOTING/quick-fixes.md).

---

## Need Help?

- **Discord**: [Join community](https://discord.gg/37XJPXfz2w)
- **GitHub Issues**: [Report problems](https://github.com/lfnovo/open-notebook/issues)
- **Docs**: See [Full Documentation](../index.md)

---

## Production Deployment

Installing for production use? See additional resources:

- [Security Hardening](https://github.com/lfnovo/open-notebook/blob/main/docs/deployment/security.md)
- [Reverse Proxy Setup](https://github.com/lfnovo/open-notebook/blob/main/docs/deployment/reverse-proxy.md)
- [Performance Tuning](https://github.com/lfnovo/open-notebook/blob/main/docs/deployment/retry-configuration.md)

---

**Ready to install?** Pick a route above! ⬆️
