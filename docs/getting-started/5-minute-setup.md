# 5-Minute Setup Guide

**Goal:** Get Open Notebook running as fast as possible.

## Step 1: Know Your Setup (10 seconds)

Answer one question: **Where will you ACCESS Open Notebook from?**

- ✅ **Same computer where Docker runs** → Use `localhost` setup below
- ✅ **Different computer** (accessing a server, Raspberry Pi, NAS, etc.) → Use `remote` setup below

## Step 2: Install Docker (if needed)

Already have Docker? Skip to Step 3.

- **Mac/Windows:** Download [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- **Linux:** `sudo apt install docker.io docker-compose-plugin`

## Step 3: Get an API Key

You need at least one AI provider. OpenAI is recommended for beginners:

1. Go to https://platform.openai.com/api-keys
2. Create account → "Create new secret key"
3. Add $5 in credits
4. Copy the key (starts with `sk-`)

## Step 4: Run Open Notebook

### 🏠 For Localhost (Same Computer):

```bash
mkdir open-notebook && cd open-notebook

cat > docker-compose.yml << 'EOF'
services:
  open_notebook:
    image: lfnovo/open_notebook:v1-latest-single
    ports:
      - "8502:8502"  # Web UI
      - "5055:5055"  # API
    environment:
      - OPENAI_API_KEY=REPLACE_WITH_YOUR_KEY
      # Database connection (required)
      - SURREAL_URL=ws://localhost:8000/rpc
      - SURREAL_USER=root
      - SURREAL_PASSWORD=root
      - SURREAL_NAMESPACE=open_notebook
      - SURREAL_DATABASE=production
    volumes:
      - ./notebook_data:/app/data
      - ./surreal_data:/mydata
    restart: always
EOF

# Edit the file and replace REPLACE_WITH_YOUR_KEY with your actual key
nano docker-compose.yml  # or use your preferred editor

docker compose up -d
```

**Access:** http://localhost:8502

### 🌐 For Remote Server:

```bash
mkdir open-notebook && cd open-notebook

cat > docker-compose.yml << 'EOF'
services:
  open_notebook:
    image: lfnovo/open_notebook:v1-latest-single
    ports:
      - "8502:8502"  # Web UI
      - "5055:5055"  # API
    environment:
      - OPENAI_API_KEY=REPLACE_WITH_YOUR_KEY
      - API_URL=http://REPLACE_WITH_SERVER_IP:5055
      # Database connection (required)
      - SURREAL_URL=ws://localhost:8000/rpc
      - SURREAL_USER=root
      - SURREAL_PASSWORD=root
      - SURREAL_NAMESPACE=open_notebook
      - SURREAL_DATABASE=production
    volumes:
      - ./notebook_data:/app/data
      - ./surreal_data:/mydata
    restart: always
EOF

# Edit the file and replace both placeholders
nano docker-compose.yml  # or use your preferred editor

docker compose up -d
```

**Find your server IP:**
```bash
# On the server where Docker is running:
hostname -I          # Linux
ipconfig             # Windows
ifconfig | grep inet # Mac
```

**Replace in the file:**
- `REPLACE_WITH_YOUR_KEY` → Your actual OpenAI key
- `REPLACE_WITH_SERVER_IP` → Your server's IP (e.g., `192.168.1.100`)

**Access:** http://YOUR_SERVER_IP:8502

## Step 5: Verify Setup

1. **Open the URL** in your browser
2. If you see "Unable to connect to server":
   - **Remote setup?** Make sure you set `API_URL` with your actual server IP
   - **Both ports exposed?** Run `docker ps` and verify you see both 8502 and 5055
   - **Using localhost for remote?** That won't work! Use the actual IP address

3. If you see the Open Notebook interface:
   - Click **Settings** → **Models**
   - Configure your default models
   - Start creating notebooks!

**Working?** → Proceed to [Your First Notebook](first-notebook.md)

**Not working?** → [Quick Troubleshooting Guide](../troubleshooting/quick-fixes.md)

## Common Mistakes to Avoid

| ❌ Wrong | ✅ Correct |
|----------|-----------|
| Only exposing port 8502 | Expose BOTH ports: 8502 and 5055 |
| Using `localhost` in API_URL for remote access | Use the actual server IP: `192.168.1.100` |
| Adding `/api` to API_URL | Just use `http://server-ip:5055` |
| Forgetting to restart after config changes | Always run `docker compose down && docker compose up -d` |

## Next Steps

Once Open Notebook is running:

1. **Configure Models** - Settings → Models
2. **Create Your First Notebook** - [Follow this guide](first-notebook.md)
3. **Add Sources** - PDFs, web links, documents
4. **Start Chatting** - Ask questions about your content
5. **Generate Podcasts** - Turn your research into audio

---

**Need help?** Join our [Discord community](https://discord.gg/37XJPXfz2w) for fast support!
