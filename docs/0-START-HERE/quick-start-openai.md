# Quick Start - OpenAI (5 minutes)

Get Open Notebook running with OpenAI's GPT models. Fast, powerful, and simple.

## Prerequisites

1. **Docker Desktop** installed
   - [Download here](https://www.docker.com/products/docker-desktop/)
   - Already have it? Skip to step 2

2. **OpenAI API Key** (required)
   - Go to https://platform.openai.com/api-keys
   - Create account → Create new secret key
   - Add at least $5 in credits to your account
   - Copy the key (starts with `sk-`)

## Step 1: Create Configuration (1 min)

Create a new folder `open-notebook` and add this file:

**docker-compose.yml**:
```yaml
services:
  surrealdb:
    image: surrealdb/surrealdb:v2
    command: start --user root --pass password --bind 0.0.0.0:8000 rocksdb:/mydata/mydatabase.db
    ports:
      - "8000:8000"
    volumes:
      - ./surreal_data:/mydata

  open_notebook:
    image: lfnovo/open_notebook:v1-latest
    pull_policy: always
    ports:
      - "8502:8502"  # Web UI
      - "5055:5055"  # API
    environment:
      # Encryption key for credential storage (required)
      - OPEN_NOTEBOOK_ENCRYPTION_KEY=change-me-to-a-secret-string

      # Database (required)
      - SURREAL_URL=ws://surrealdb:8000/rpc
      - SURREAL_USER=root
      - SURREAL_PASSWORD=password
      - SURREAL_NAMESPACE=open_notebook
      - SURREAL_DATABASE=open_notebook
    volumes:
      - ./notebook_data:/app/data
    depends_on:
      - surrealdb
    restart: always

```

**Edit the file:**
- Replace `change-me-to-a-secret-string` with your own secret (any string works)

---

## Step 2: Start Services (1 min)

Open terminal in your `open-notebook` folder:

```bash
docker compose up -d
```

Wait 15-20 seconds for services to start.

---

## Step 3: Access Open Notebook (instant)

Open your browser:
```
http://localhost:8502
```

You should see the Open Notebook interface!

---

## Step 4: Configure Your OpenAI Provider (1 min)

1. Go to **Settings** → **API Keys**
2. Click **Add Credential**
3. Select provider: **OpenAI**
4. Give it a name (e.g., "My OpenAI Key")
5. Paste your OpenAI API key
6. Click **Save**
7. Click **Test Connection** — should show success
8. Click **Discover Models** → **Register Models**

Your OpenAI models are now available!

---

## Step 5: Create Your First Notebook (1 min)

1. Click **New Notebook**
2. Name: "My Research"
3. Click **Create**

---

## Step 6: Add a Source (1 min)

1. Click **Add Source**
2. Choose **Web Link**
3. Paste: `https://en.wikipedia.org/wiki/Artificial_intelligence`
4. Click **Add**
5. Wait for processing (30-60 seconds)

---

## Step 7: Chat With Your Content (1 min)

1. Go to **Chat**
2. Type: "What is artificial intelligence?"
3. Click **Send**
4. Watch as GPT responds with information from your source!

---

## Verification Checklist

- [ ] Docker is running
- [ ] You can access `http://localhost:8502`
- [ ] OpenAI credential is configured and tested
- [ ] You created a notebook
- [ ] You added a source
- [ ] Chat works

**All checked?** You have a fully working AI research assistant!

---

## Using Different Models

In your notebook, go to **Settings** → **Models** to choose:
- `gpt-4o` - Best quality (recommended)
- `gpt-4o-mini` - Fast and cheap (good for testing)

---

## Troubleshooting

### "Port 8502 already in use"

Change the port in docker-compose.yml:
```yaml
ports:
  - "8503:8502"  # Use 8503 instead
```

Then access at `http://localhost:8503`

### "API key not working"

1. Go to **Settings** → **API Keys**
2. Click **Test Connection** on your OpenAI credential
3. If it fails, verify your key at https://platform.openai.com
4. Delete the credential and create a new one with the correct key

### "Cannot connect to server"

```bash
docker ps  # Check all services running
docker compose logs  # View logs
docker compose restart  # Restart everything
```

---

## Next Steps

1. **Add Your Own Content**: PDFs, web links, documents
2. **Explore Features**: Podcasts, transformations, search
3. **Full Documentation**: [See all features](../3-USER-GUIDE/index.md)

---

## Cost Estimate

OpenAI pricing (approximate):
- **Conversation**: $0.01-0.10 per 1K tokens
- **Embeddings**: $0.02 per 1M tokens
- **Typical usage**: $1-5/month for light use, $20-50/month for heavy use

Check https://openai.com/pricing for current rates.

---

**Need help?** Join our [Discord community](https://discord.gg/37XJPXfz2w)!
