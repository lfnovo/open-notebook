# Deployment Guide

This section provides comprehensive guides for deploying Open Notebook in different environments, from simple local setups to production deployments.

## 🚀 Quick Start

**New to Open Notebook?** Start with the [Docker Setup Guide](docker.md) - it's the fastest way to get up and running.

## 📋 Deployment Options

### 1. [Docker Deployment](docker.md)
**Recommended for most users**
- Complete beginner-friendly guide
- Single-container and multi-container options
- Supports all major AI providers
- Perfect for local development and testing

### 2. [Single Container Deployment](single-container.md)
**Best for platforms like PikaPods**
- All-in-one container solution
- Simplified deployment process
- Ideal for cloud hosting platforms
- Lower resource requirements

### 3. [Development Setup](development.md)
**For contributors and advanced users**
- Local development environment
- Source code installation
- Development tools and debugging
- Contributing to the project

### 4. [Reverse Proxy Configuration](reverse-proxy.md)
**For production deployments with custom domains**
- nginx, Caddy, Traefik configurations
- Custom domain setup
- SSL/HTTPS configuration
- Runtime API URL configuration

### 5. [Security Configuration](security.md)
**Essential for public deployments**
- Password protection setup
- Security best practices
- Production deployment considerations
- Troubleshooting security issues

### 6. [Retry Configuration](retry-configuration.md)
**For reliable background job processing**
- Automatic retry for transient failures
- Database transaction conflict handling
- Embedding provider failure recovery
- Performance tuning and monitoring

## 🎯 Choose Your Deployment Method

### Use Docker Setup if:
- You're new to Open Notebook
- You want the easiest setup experience
- You need multiple AI provider support
- You're running locally or on a private server

### Use Single Container if:
- You're deploying on PikaPods, Railway, or similar platforms
- You want the simplest possible deployment
- You have resource constraints
- You don't need to scale services independently

### Use Reverse Proxy Setup if:
- You're deploying with a custom domain
- You need HTTPS/SSL encryption
- You're using nginx, Caddy, or Traefik
- You want to expose only specific ports publicly

### Use Development Setup if:
- You want to contribute to the project
- You need to modify the source code
- You're developing integrations or plugins
- You want to understand the codebase

## 📚 Additional Resources

### Before You Start
- **[System Requirements](#system-requirements)** - Hardware and software needs
- **[API Keys Guide](#api-keys)** - Getting keys from AI providers
- **[Environment Variables](#environment-variables)** - Configuration reference

### After Deployment
- **[First Notebook Guide](../getting-started/first-notebook.md)** - Create your first research project
- **[User Guide](../user-guide/index.md)** - Learn all the features
- **[Troubleshooting](../troubleshooting/index.md)** - Common issues and solutions

## 🔧 System Requirements

### Minimum Requirements
- **Memory**: 2GB RAM
- **CPU**: 2 cores
- **Storage**: 10GB free space
- **Network**: Internet connection for AI providers

### Recommended Requirements
- **Memory**: 4GB+ RAM
- **CPU**: 4+ cores
- **Storage**: 50GB+ free space
- **Network**: Stable high-speed internet

### Platform Support
- **Linux**: Ubuntu 20.04+, CentOS 7+, or similar
- **Windows**: Windows 10+ with WSL2 (for Docker)
- **macOS**: macOS 10.14+
- **Docker**: Version 20.10+ required

## 🔑 API Keys

Open Notebook supports multiple AI providers. You'll need at least one:

### Required for Basic Functionality
- **OpenAI**: For GPT models, embeddings, and TTS
  - Get your key at [platform.openai.com](https://platform.openai.com)
  - Provides: Language models, embeddings, speech services

### Optional Providers
- **Anthropic**: For Claude models
- **Google**: For Gemini models
- **Groq**: For fast inference
- **Ollama**: For local models (no API key needed)

See the [Model Providers Guide](../model-providers.md) for detailed setup instructions.

## 🌍 Environment Variables

### Core Configuration
```bash
# Database (auto-configured in Docker)
SURREAL_URL=ws://localhost:8000/rpc
SURREAL_USER=root
SURREAL_PASSWORD=root
SURREAL_NAMESPACE=open_notebook
SURREAL_DATABASE=production

# Security (optional)
OPEN_NOTEBOOK_PASSWORD=your_secure_password
```

### AI Provider Keys
```bash
# OpenAI (recommended)
OPENAI_API_KEY=sk-...

# Additional providers (optional)
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=AIzaSy...
GROQ_API_KEY=gsk_...
OLLAMA_API_BASE=http://localhost:11434
```

## 🆘 Getting Help

### Community Support
- **[Discord Server](https://discord.gg/37XJPXfz2w)** - Real-time help and discussion
- **[GitHub Issues](https://github.com/lfnovo/open-notebook/issues)** - Bug reports and feature requests
- **[GitHub Discussions](https://github.com/lfnovo/open-notebook/discussions)** - Questions and ideas

### Documentation
- **[User Guide](../user-guide/index.md)** - Complete feature documentation
- **[Troubleshooting](../troubleshooting/index.md)** - Common issues and solutions
- **[API Reference](../api-reference.md)** - REST API documentation

## 📞 Support

Having trouble with deployment? Here's how to get help:

1. **Check the troubleshooting section** in each deployment guide
2. **Search existing issues** on GitHub
3. **Ask on Discord** for real-time help
4. **Create a GitHub issue** for bugs or feature requests

Remember to include:
- Your operating system and version
- Deployment method used
- Error messages (if any)
- Steps to reproduce the issue

---

**Ready to deploy?** Choose your deployment method above and follow the step-by-step guide!