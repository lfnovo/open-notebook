# Open Notebook - Advanced Docker Setup Guide

**Ready to supercharge your Open Notebook experience? This guide covers advanced AI providers and configurations.**

## Prerequisites

Before following this guide, you should have:
- ✅ Completed the [basic Docker setup guide](DOCKER_SETUP_GUIDE.md)
- ✅ Open Notebook running successfully with OpenAI
- ✅ Created your first notebook and added some sources

## Overview: Why Go Advanced?

While OpenAI provides excellent all-in-one functionality, you might want to explore:
- **More AI models**: Access to Claude, Gemini, Llama, and 100+ others
- **Cost optimization**: Some providers offer better pricing for specific tasks
- **Privacy**: Run models locally on your computer
- **Specialized models**: Better performance for specific use cases

## Option 1: Add OpenRouter (Recommended)

OpenRouter gives you access to virtually every AI model available today through a single API.

### Why OpenRouter?
- **100+ models**: Claude, Gemini, Llama, Mistral, and more
- **Cost-effective**: Often cheaper than going direct to providers
- **Easy integration**: Works alongside your existing OpenAI setup
- **No upfront costs**: Pay as you go

### Getting Your OpenRouter API Key

1. Go to https://openrouter.ai/keys
2. Create an account or sign in
3. Click **"Create Key"**
4. Copy the key (starts with "sk-or-")
5. **No upfront payment required** - you can start using many models immediately

### Adding OpenRouter to Your Configuration

1. **Stop Open Notebook**:
   ```bash
   docker-compose down
   ```

2. **Edit your `docker.env` file** and add the OpenRouter key:
   ```env
   # REQUIRED: Your OpenAI API key
   OPENAI_API_KEY=YOUR_OPENAI_API_KEY_HERE
   
   # OPTIONAL: OpenRouter for access to many models
   OPENROUTER_API_KEY=YOUR_OPENROUTER_API_KEY_HERE
   
   # Database settings (don't change these)
   SURREAL_ADDRESS=surrealdb
   SURREAL_PORT=8000
   SURREAL_USER=root
   SURREAL_PASS=root
   SURREAL_NAMESPACE=open_notebook
   SURREAL_DATABASE=production
   ```

3. **Start Open Notebook again**:
   ```bash
   docker-compose up -d
   ```

4. **Configure new models**:
   - Go to Settings → Models
   - You'll now see many more model options from different providers
   - Try models like `anthropic/claude-3-haiku` or `google/gemini-pro`

### Recommended OpenRouter Models

**For Chat (Alternative to GPT-4)**:
- `anthropic/claude-3-haiku` - Fast and cost-effective
- `google/gemini-pro` - Good reasoning capabilities
- `meta-llama/llama-3-8b-instruct` - Open source option

**For Advanced Tasks**:
- `anthropic/claude-3-opus` - Best quality for complex tasks
- `google/gemini-pro-1.5` - Excellent for long context

**For Cost-Conscious Users**:
- `meta-llama/llama-3-8b-instruct` - Very affordable
- `mistral/mistral-7b-instruct` - Good balance of cost and quality

## Option 2: Add Ollama (Local Models)

Run AI models directly on your computer for complete privacy and no API costs.

### Why Ollama?
- **Complete privacy**: Your data never leaves your computer
- **No API costs**: Free to use once set up
- **Offline capability**: Works without internet connection
- **Control**: Full control over your AI models

### Requirements
- **Powerful computer**: 16GB RAM minimum, 32GB recommended
- **Good CPU/GPU**: Modern processor, GPU acceleration helpful
- **Disk space**: 4-20GB per model

### Installing Ollama

1. **Download Ollama**: Go to https://ollama.ai and download for your system
2. **Install the application** following the instructions for your OS
3. **Start Ollama**: Run `ollama serve` in terminal
4. **Download models**: 
   ```bash
   ollama pull llama2        # 7B model (~4GB)
   ollama pull mistral       # 7B model (~4GB)
   ollama pull llama2:13b    # 13B model (~8GB) - better quality
   ```

### Configuring Ollama with Docker

Docker containers can't use "localhost" to reach your computer, so we need to configure the IP address.

1. **Find your computer's IP address**:
   - **Windows**: Open Command Prompt, run `ipconfig`, look for "IPv4 Address"
   - **macOS**: Open Terminal, run `ifconfig | grep inet`, look for your local IP
   - **Linux**: Run `ip addr show` or `hostname -I`
   - Your IP will be something like `192.168.1.100` or `10.0.0.50`

2. **Stop Open Notebook**:
   ```bash
   docker-compose down
   ```

3. **Edit your `docker.env` file** and add the Ollama configuration:
   ```env
   # REQUIRED: Your OpenAI API key
   OPENAI_API_KEY=YOUR_OPENAI_API_KEY_HERE
   
   # OPTIONAL: OpenRouter for access to many models
   OPENROUTER_API_KEY=YOUR_OPENROUTER_API_KEY_HERE
   
   # OPTIONAL: Ollama for local models
   # Replace 192.168.1.100 with your actual IP address
   OLLAMA_API_BASE=http://192.168.1.100:11434
   
   # Database settings (don't change these)
   SURREAL_ADDRESS=localhost
   SURREAL_PORT=8000
   SURREAL_USER=root
   SURREAL_PASS=root
   SURREAL_NAMESPACE=open_notebook
   SURREAL_DATABASE=production
   ```

4. **Make sure your firewall allows connections** to port 11434

5. **Start Open Notebook**:
   ```bash
   docker-compose up -d
   ```

6. **Test the connection**:
   - Go to Settings → Models
   - You should see your Ollama models listed
   - If not, double-check your IP address and firewall settings

### Recommended Ollama Models

**For Beginners**:
- `llama2` (7B) - Good balance of quality and speed
- `mistral` (7B) - Fast and capable

**For Better Quality** (requires more RAM):
- `llama2:13b` (13B) - Better responses, slower
- `codellama` (7B) - Great for programming tasks

**For Advanced Users**:
- `llama2:70b` (70B) - Excellent quality, requires 64GB+ RAM
- `mistral:7b-instruct` - Fine-tuned for following instructions

## Option 3: Additional Providers

### Anthropic (Claude Direct)
If you want to use Claude directly instead of through OpenRouter:

1. Get your API key at https://console.anthropic.com/
2. Add to `docker.env`:
   ```env
   ANTHROPIC_API_KEY=YOUR_ANTHROPIC_API_KEY_HERE
   ```

### Google Gemini (Direct)
For direct access to Google's models:

1. Get your API key at https://makersuite.google.com/app/apikey
2. Add to `docker.env`:
   ```env
   GEMINI_API_KEY=YOUR_GEMINI_API_KEY_HERE
   ```

### Groq (Fast Inference)
For very fast model inference:

1. Get your API key at https://console.groq.com/keys
2. Add to `docker.env`:
   ```env
   GROQ_API_KEY=YOUR_GROQ_API_KEY_HERE
   ```

## Complete Configuration Example

Here's a complete `docker.env` file with all providers:

```env
# REQUIRED: Your OpenAI API key
OPENAI_API_KEY=sk-1234567890abcdef...

# OPTIONAL: Additional providers
OPENROUTER_API_KEY=sk-or-v1-1234567890abcdef...
ANTHROPIC_API_KEY=sk-ant-1234567890abcdef...
GEMINI_API_KEY=AIzaSy1234567890abcdef...
GROQ_API_KEY=gsk_1234567890abcdef...

# OPTIONAL: Ollama for local models
OLLAMA_API_BASE=http://192.168.1.100:11434

# OPTIONAL: For podcast generation
ELEVENLABS_API_KEY=sk_1234567890abcdef...

# Database settings (don't change these)
SURREAL_ADDRESS=surrealdb
SURREAL_PORT=8000
SURREAL_USER=root
SURREAL_PASS=root
SURREAL_NAMESPACE=open_notebook
SURREAL_DATABASE=production
```

## Advanced Model Configuration Tips

### Cost Optimization
- Use **OpenRouter** for expensive models (Claude, GPT-4)
- Use **Ollama** for simple tasks to save API costs
- Monitor usage at each provider's dashboard

### Performance Optimization
- Use **Groq** for fast inference when speed matters
- Use **local models** when privacy is crucial
- Use **OpenAI** for best reliability and features

### Specialized Tasks
- **Code generation**: `codellama` (Ollama) or `gpt-4` (OpenAI)
- **Long documents**: `claude-3-opus` (Anthropic) or `gemini-pro-1.5` (Google)
- **Creative writing**: `claude-3-opus` (Anthropic) or `gpt-4` (OpenAI)

## Troubleshooting Advanced Setups

### OpenRouter Issues
- **Models not appearing**: Check your API key is correct
- **Rate limits**: Some models have usage limits
- **Costs**: Monitor usage at https://openrouter.ai/activity

### Ollama Issues
- **Models not detected**: Check IP address and firewall
- **Slow performance**: Try smaller models or upgrade hardware
- **Connection refused**: Ensure `ollama serve` is running

### General Tips
- **Start small**: Add one provider at a time
- **Test thoroughly**: Verify each provider works before adding more
- **Monitor costs**: Set up billing alerts for cloud providers
- **Keep backups**: Save working configurations

## Getting Help

- **Discord**: Join our community at https://discord.gg/37XJPXfz2w
- **GitHub Issues**: Report problems at https://github.com/lfnovo/open-notebook/issues
- **Documentation**: Visit https://www.open-notebook.ai

## What's Next?

With your advanced setup complete, you can:
- **Experiment with different models** for various tasks
- **Compare quality and costs** across providers
- **Build custom workflows** using the best model for each task
- **Contribute to the project** by sharing your experience

Happy exploring! 🚀