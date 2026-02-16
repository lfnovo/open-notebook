# API Configuration

Configure AI provider credentials through the Settings UI. No file editing required.

> **Credential System**: Open Notebook uses encrypted credentials stored in the database. Each credential connects to a provider and allows you to discover, register, and test models.

---

## Overview

Open Notebook manages AI provider access through a **credential-based system**:

1. You create a **credential** for each provider (API key + settings)
2. Credentials are **encrypted** and stored in the database
3. You **test connections** to verify credentials work
4. You **discover and register models** from each credential
5. Models are linked to credentials for direct configuration

---

## Encryption Setup

Before storing credentials, you must configure an encryption key.

### Setting the Encryption Key

Add `OPEN_NOTEBOOK_ENCRYPTION_KEY` to your docker-compose.yml:

```yaml
environment:
  - OPEN_NOTEBOOK_ENCRYPTION_KEY=my-secret-passphrase
```

Any string works as a key — it will be securely derived via SHA-256 internally.

> **Warning**: If you change or lose the encryption key, **all stored credentials become unreadable**. Back up your encryption key securely and separately from your database backups.

### Docker Secrets Support

Both password and encryption key support Docker secrets:

```yaml
# docker-compose.yml
services:
  open_notebook:
    environment:
      - OPEN_NOTEBOOK_PASSWORD_FILE=/run/secrets/app_password
      - OPEN_NOTEBOOK_ENCRYPTION_KEY_FILE=/run/secrets/encryption_key
    secrets:
      - app_password
      - encryption_key

secrets:
  app_password:
    file: ./secrets/password.txt
  encryption_key:
    file: ./secrets/encryption_key.txt
```

### Encryption Details

API keys stored in the database are encrypted using Fernet (AES-128-CBC + HMAC-SHA256).

| Configuration | Behavior |
|---------------|----------|
| Encryption key set | Keys encrypted with your key |
| No encryption key set | Storing credentials is disabled |

---

## Accessing Credential Configuration

1. Click **Settings** in the navigation bar
2. Select **API Keys** tab
3. You'll see existing credentials and an **Add Credential** button

```
Navigation: Settings → API Keys
```

---

## Supported Providers

### Cloud Providers

| Provider | Required Fields | Optional Fields |
|----------|-----------------|-----------------|
| OpenAI | API Key | — |
| Anthropic | API Key | — |
| Google Gemini | API Key | — |
| Groq | API Key | — |
| Mistral | API Key | — |
| DeepSeek | API Key | — |
| xAI | API Key | — |
| OpenRouter | API Key | — |
| Voyage AI | API Key | — |
| ElevenLabs | API Key | — |

### Local/Self-Hosted

| Provider | Required Fields | Notes |
|----------|-----------------|-------|
| Ollama | Base URL | Typically `http://localhost:11434` or `http://ollama:11434` |

### Enterprise

| Provider | Required Fields | Optional Fields |
|----------|-----------------|-----------------|
| Azure OpenAI | API Key, Endpoint, API Version | Service-specific endpoints (LLM, Embedding, STT, TTS) |
| OpenAI-Compatible | Base URL | API Key, Service-specific configs |
| Vertex AI | Project ID, Location, Credentials Path | — |

---

## Creating a Credential

### Step 1: Add Credential

1. Go to **Settings** → **API Keys**
2. Click **Add Credential**
3. Select your provider
4. Give it a descriptive name (e.g., "My OpenAI Key", "Work Anthropic")
5. Fill in the required fields (API key, base URL, etc.)
6. Click **Save**

### Step 2: Test Connection

1. On your new credential card, click **Test Connection**
2. Wait for the result:

| Result | Meaning |
|--------|---------|
| Success | Key is valid, provider accessible |
| Invalid API key | Check key format and value |
| Connection failed | Check URL, network, firewall |

### Step 3: Discover Models

1. Click **Discover Models** on the credential card
2. The system queries the provider for available models
3. Review the discovered models

### Step 4: Register Models

1. Select the models you want to use
2. Click **Register Models**
3. The models are now available throughout Open Notebook

---

## Multi-Credential Support

Each provider can have **multiple credentials**. This is useful when:
- You have different API keys for different projects
- You want to test with different endpoints
- Multiple team members need separate credentials

### Creating Multiple Credentials

1. Click **Add Credential** again
2. Select the same provider
3. Fill in different credentials
4. Each credential can discover and register its own models

### How Models Link to Credentials

When you register models from a credential, those models are linked to that specific credential. This means:
- Each model knows which API key to use
- You can have models from different credentials for the same provider
- Deleting a credential removes its linked models

---

## Testing Connections

Click **Test Connection** to verify your credential:

| Result | Meaning |
|--------|---------|
| Success | Key is valid, provider accessible |
| Invalid API key | Check key format and value |
| Connection failed | Check URL, network, firewall |
| Model not available | Key valid but model access restricted |

Test uses inexpensive models (e.g., `gpt-3.5-turbo`, `claude-3-haiku`) to minimize cost.

---

## Configuring Specific Providers

### Simple Providers (API Key Only)

For OpenAI, Anthropic, Google, Groq, Mistral, DeepSeek, xAI, OpenRouter:

1. Add credential with your API key
2. Test connection
3. Discover and register models

### Ollama (URL-Based)

1. Add credential with provider **Ollama**
2. Enter the base URL (e.g., `http://ollama:11434`)
3. Test connection
4. Discover and register models

Ollama allows localhost and private IPs since it runs locally.

### Azure OpenAI

Azure requires multiple fields:

| Field | Example | Required |
|-------|---------|----------|
| API Key | `abc123...` | Yes |
| Endpoint | `https://myresource.openai.azure.com` | Yes |
| API Version | `2024-02-15-preview` | Yes |
| LLM Endpoint | `https://myresource-llm.openai.azure.com` | No |
| Embedding Endpoint | `https://myresource-embed.openai.azure.com` | No |

Service-specific endpoints override the main endpoint for that service type.

### OpenAI-Compatible

For custom OpenAI-compatible servers (LM Studio, vLLM, etc.):

1. Add credential with provider **OpenAI-Compatible**
2. Enter the base URL
3. Enter API key (if required)
4. Optionally configure per-service URLs

Supports separate configurations for:
- LLM (language models)
- Embedding
- STT (speech-to-text)
- TTS (text-to-speech)

### Vertex AI

Google Cloud's enterprise AI platform:

| Field | Example |
|-------|---------|
| Project ID | `my-gcp-project` |
| Location | `us-central1` |
| Credentials Path | `/path/to/service-account.json` |

---

## Migrating from Environment Variables

If you have existing API keys in environment variables (from a previous version):

1. Open **Settings → API Keys**
2. A banner appears: "Environment variables detected"
3. Click **Migrate to Database**
4. Keys are copied to the database (encrypted)
5. Original environment variables remain unchanged

### Migration Behavior

| Scenario | Action |
|----------|--------|
| Key in env only | Migrated to database |
| Key in database only | No change |
| Key in both | Database version kept (skipped) |

### After Migration

- Database credentials are used for all operations
- You can remove the API key environment variables from your docker-compose.yml
- Keep `OPEN_NOTEBOOK_ENCRYPTION_KEY` — it's still required

### Migration Banner Visibility

The migration banner only appears when:
- You have environment variables configured
- Those providers are **not** already in the database
- If all env providers are already migrated, the banner won't show

---

## Migrating from ProviderConfig (v1.1 → v1.2)

If you're upgrading from an older version that used the ProviderConfig system:

- The migration happens automatically on first startup
- Your existing configurations are converted to credentials
- Check **Settings → API Keys** to verify the migration succeeded
- If you see issues, check the API logs for migration messages

---

## Key Storage Security

### Encryption

API keys stored in the database are encrypted using Fernet (AES-128-CBC + HMAC-SHA256).

| Configuration | Behavior |
|---------------|----------|
| Encryption key set | Keys encrypted with your key |
| No encryption key set | Storing API keys in database is disabled |

### Default Credentials

| Setting | Default Value | Production Recommendation |
|---------|---------------|---------------------------|
| Password | `open-notebook-change-me` | Set `OPEN_NOTEBOOK_PASSWORD` |
| Encryption Key | None (must be set) | Set `OPEN_NOTEBOOK_ENCRYPTION_KEY` to any secret string |

**For production deployments, always set custom credentials.**

---

## Deleting Credentials

1. Click the **Delete** button on the credential card
2. Confirm deletion
3. Credential and all its linked models are removed from the database

---

## Troubleshooting

### Credential Not Saving

| Symptom | Cause | Solution |
|---------|-------|----------|
| Save button disabled | Empty or invalid input | Enter a valid key |
| Error on save | Encryption key not set | Set `OPEN_NOTEBOOK_ENCRYPTION_KEY` in docker-compose.yml |
| Error on save | Database connection issue | Check database status |

### Test Connection Fails

| Error | Cause | Solution |
|-------|-------|----------|
| Invalid API key | Wrong key or format | Verify key from provider dashboard |
| Connection refused | Wrong URL | Check base URL format |
| Timeout | Network issue | Check firewall, proxy settings |
| 403 Forbidden | IP restriction | Whitelist your server IP |

### Migration Issues

| Problem | Solution |
|---------|----------|
| No migration banner | No env vars detected, or already migrated |
| Partial migration | Check error list, fix and retry |
| Keys not working after migration | Clear browser cache, restart services |

### Provider Shows "Not Configured"

1. Check if a credential exists for this provider (Settings → API Keys)
2. Test the credential connection
3. Verify key format matches provider requirements
4. Re-discover and register models if needed

---

## Provider-Specific Notes

### OpenAI
- Keys start with `sk-proj-` (project keys) or `sk-` (legacy)
- Requires billing enabled on account

### Anthropic
- Keys start with `sk-ant-`
- Check account has API access enabled

### Google Gemini
- Keys start with `AIzaSy`
- Free tier has rate limits

### Ollama
- No API key required
- Default URL: `http://localhost:11434` (local) or `http://ollama:11434` (Docker)
- Ensure Ollama server is running

### Azure OpenAI
- Endpoint format: `https://{resource-name}.openai.azure.com`
- API version format: `YYYY-MM-DD` or `YYYY-MM-DD-preview`
- Deployment names configured separately when registering models via the credential's Discover Models dialog

---

## Related

- **[AI Providers](../5-CONFIGURATION/ai-providers.md)** — Provider setup instructions and recommendations
- **[Security](../5-CONFIGURATION/security.md)** — Password and encryption configuration
- **[Environment Reference](../5-CONFIGURATION/environment-reference.md)** — All configuration options
