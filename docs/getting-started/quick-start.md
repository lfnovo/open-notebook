# Quick Start Guide - Get Open Notebook Running in 5 Minutes

Get up and running with Open Notebook in just a few minutes! This guide will get you from zero to your first AI-powered notebook quickly.

## Prerequisites

Before starting, ensure you have:

1. **Docker Desktop** installed and running
   - [Download for Windows/Mac](https://www.docker.com/products/docker-desktop/)
   - Linux: `sudo apt install docker.io docker-compose`

2. **OpenAI API Key** (recommended for beginners)
   - Go to [OpenAI Platform](https://platform.openai.com/)
   - Create account → API Keys → Create new secret key
   - Add $5+ credits to your account for API usage

## Single Command Setup

### Step 1: Choose Your Setup Method

Are you installing on:
- **🏠 The same computer** you'll use to access Open Notebook? → Use **Local Setup**
- **🌐 A remote server** (Raspberry Pi, NAS, cloud server, Proxmox)? → Use **Remote Setup**

### Step 2: Create Your Configuration

Create a new folder called `open-notebook` and add these files:

#### For Local Machine (Same Computer):

**docker-compose.yml**:
```yaml
services:
  open_notebook:
    image: lfnovo/open_notebook:v1-latest-single
    ports:
      - "8502:8502"  # Web UI
      - "5055:5055"  # API (required!)
    env_file:
      - ./docker.env
    pull_policy: always
    volumes:
      - ./notebook_data:/app/data
      - ./surreal_single_data:/mydata
    restart: always
```

**docker.env**:
```env
# Replace YOUR_OPENAI_API_KEY_HERE with your actual API key
OPENAI_API_KEY=YOUR_OPENAI_API_KEY_HERE

# Database connection (required for single-container)
SURREAL_URL="ws://localhost:8000/rpc"
SURREAL_USER="root"
SURREAL_PASSWORD="root"
SURREAL_NAMESPACE="open_notebook"
SURREAL_DATABASE="production"
```

#### For Remote Server:

**docker-compose.yml**:
```yaml
services:
  open_notebook:
    image: lfnovo/open_notebook:v1-latest-single
    ports:
      - "8502:8502"  # Web UI
      - "5055:5055"  # API (required!)
    env_file:
      - ./docker.env
    pull_policy: always
    volumes:
      - ./notebook_data:/app/data
      - ./surreal_single_data:/mydata
    restart: always
```

**docker.env**:
```env
# Replace YOUR_OPENAI_API_KEY_HERE with your actual API key
OPENAI_API_KEY=YOUR_OPENAI_API_KEY_HERE

# CRITICAL: Replace YOUR_SERVER_IP with your server's actual IP address
# Example: API_URL=http://192.168.1.100:5055
API_URL=http://YOUR_SERVER_IP:5055

# Database connection (required for single-container)
SURREAL_URL="ws://localhost:8000/rpc"
SURREAL_USER="root"
SURREAL_PASSWORD="root"
SURREAL_NAMESPACE="open_notebook"
SURREAL_DATABASE="production"
```

> **⚠️ Finding Your Server IP:**
> On the server running Docker, use:
> - **Linux**: `hostname -I` or `ip addr show`
> - **Windows**: `ipconfig` (look for IPv4 Address)
> - **Mac**: `ifconfig | grep inet`

### Step 3: Start Open Notebook

Open terminal/command prompt in your `open-notebook` folder and run:

```bash
docker compose up -d
```

**That's it!** Open Notebook is now running.

**Access at:**
- **Local setup**: http://localhost:8502
- **Remote setup**: http://YOUR_SERVER_IP:8502 (replace with your actual IP)

## Basic Verification

1. **Check Services**: Visit http://localhost:8502 - you should see the Open Notebook interface
2. **API Health**: Visit http://localhost:5055/docs - you should see the API documentation
3. **No Errors**: Run `docker-compose logs` to ensure no error messages

## Simple Example Workflow

### 1. Configure AI Models
- Click **Models** in the sidebar
- Set these recommended models:
  - **Language Model**: `gpt-5-mini`
  - **Embedding Model**: `text-embedding-3-small`
  - **Text-to-Speech**: `gpt-4o-mini-tts`
  - **Speech-to-Text**: `whisper-1`
- Click **Save**

### 2. Create Your First Notebook
- Click **"Create New Notebook"**
- Name: "My Research"
- Description: "Getting started with Open Notebook"
- Click **"Create"**

### 3. Add a Source
- Click **"Add Source"**
- Choose **"Link"** and paste: `https://en.wikipedia.org/wiki/Artificial_intelligence`
- Click **"Add Source"**
- Wait for processing to complete

### 4. Generate Your First Note
- Go to the **Notes** column
- Click **"Create AI Note"**
- Enter prompt: "Summarize the key concepts of artificial intelligence"
- Click **"Generate Note"**
- Watch as AI creates a comprehensive summary!

### 5. Chat with Your Content
- Go to the **Chat** column
- Ask: "What are the main applications of AI mentioned in the source?"
- Get instant answers with citations from your content

## Next Steps

Now that you have Open Notebook running:

### Essential Features to Explore
- **📁 [Content Support](../content-support.md)** - Learn what file types you can add
- **🔍 [Search](../search.md)** - Master full-text and vector search
- **🎙️ [Podcast Generation](../features/podcasts.md)** - Create multi-speaker podcasts from your research
- **⚙️ [Transformations](../features/transformations.md)** - Extract insights and summaries

### Advanced Setup
- **🔧 [Development Setup](../development/)** - Run from source code
- **☁️ [Deployment](../deployment/)** - Deploy to cloud services
- **🤖 [AI Models](../features/ai-models.md)** - Add more AI providers beyond OpenAI

### Getting Help
- **💬 [Discord Community](https://discord.gg/37XJPXfz2w)** - Get help and share ideas
- **📖 [Full Documentation](../user-guide/)** - Complete feature guide
- **🐛 [Report Issues](https://github.com/lfnovo/open-notebook/issues)** - Found a bug?

## Common Issues

### ❌ "Unable to connect to server" Error

**This is the #1 issue!** The frontend can't reach the API.

**Quick Fix Checklist:**

1. **Are you accessing from a different computer than where Docker runs?**
   - ✅ Yes → You MUST set `API_URL` in your `docker.env` (see Remote Setup above)
   - ❌ No → Skip to step 2

2. **Is port 5055 exposed?**
   ```bash
   docker ps
   # Should show both: 0.0.0.0:8502->8502 AND 0.0.0.0:5055->5055
   ```
   - ❌ Missing 5055? Add it to your `docker-compose.yml` ports section

3. **Restart after changes:**
   ```bash
   docker compose down
   docker compose up -d
   ```

**Still not working?** See the [complete troubleshooting guide](../troubleshooting/quick-fixes.md).

### API Key Errors
- Double-check your API key in `docker.env`
- Ensure you have credits in your OpenAI account
- Verify no extra spaces around the key
- Key should start with `sk-`

### Port Already in Use
```bash
docker compose down
docker compose up -d
```

### Container Won't Start
```bash
docker compose down -v
docker compose up -d
```

### Can't Access Interface
- Ensure Docker Desktop is running
- Check firewall isn't blocking ports 8502 and 5055
- Try: `docker compose restart`

## Stopping Open Notebook

To stop:
```bash
docker-compose down
```

To start again:
```bash
docker-compose up -d
```

---

**Congratulations!** You now have Open Notebook running and ready for your research workflow. Start by adding your own documents and see how AI can enhance your note-taking and research process.

**Next recommended read**: [Basic Workflow Guide](../basic-workflow.md) to learn effective research patterns.