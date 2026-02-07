# API Configuration

Configure AI provider API keys directly through the Settings UI. No file editing required.

> 💡 **New Feature**: You can now create **multiple configurations** per provider (e.g., different API keys for different projects). See [Multi-Config Support](#multi-config-support) for details.

---

## Overview

Open Notebook supports two methods for configuring API keys:

| Method | Best For | Requires |
|--------|----------|----------|
| **Settings UI** | Most users, quick setup | Browser access |
| **Environment Variables** | DevOps, automation, CI/CD | File access |

Both methods work together. Database-stored keys take priority over environment variables.

---

## Accessing API Configuration

1. Click **Settings** in the navigation bar
2. Select **API Keys** tab
3. Find your provider in the list

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
| Ollama | Base URL | Typically `http://localhost:11434` |

### Enterprise

| Provider | Required Fields | Optional Fields |
|----------|-----------------|-----------------|
| Azure OpenAI | API Key, Endpoint, API Version | Service-specific endpoints (LLM, Embedding, STT, TTS) |
| OpenAI-Compatible | Base URL | API Key, Service-specific configs |
| Vertex AI | Project ID, Location, Credentials Path | — |

---

## Configuring a Provider

### Simple Providers (API Key Only)

1. Locate the provider card
2. Enter your API key
3. Click **Save**
4. Click **Test Connection** to verify

```
Example: OpenAI
┌─────────────────────────────────────┐
│ OpenAI                    [Status]  │
├─────────────────────────────────────┤
│ API Key: ●●●●●●●●●●●●              │
│                                     │
│ [Test Connection]  [Save]  [Delete] │
└─────────────────────────────────────┘
```

### URL-Based Providers (Ollama)

1. Enter the base URL (e.g., `http://localhost:11434`)
2. Click **Save**
3. Click **Test Connection**

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

1. Enter the base URL
2. Enter API key (if required)
3. Optionally configure per-service URLs

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

## Multi-Config Support

Each provider can now have **multiple configurations**. This is useful when:
- You have different API keys for different projects
- You want to test with different models/endpoints
- Multiple team members need separate credentials

### Creating Multiple Configs

1. On a provider's card, click **Add Configuration**
2. Fill in the configuration details
3. Click **Save**
4. Use the star icon to set a default configuration

```
Example: OpenAI with multiple configs
┌─────────────────────────────────────────────────┐
│ OpenAI                              [+ Add Config] │
├─────────────────────────────────────────────────┤
│ ★ Default (api.openai.com)           [Edit] [Delete] │
│ ✦ Work Key (work.openai.com)         [Edit] [Delete] │
└─────────────────────────────────────────────────┘
```

### Managing Configurations

| Action | How |
|--------|-----|
| Add new config | Click **[+ Add Configuration]** on provider card |
| Edit config | Click **[Edit]** on the config |
| Delete config | Click **[Delete]** on the config |
| Set default | Click **star icon** on the config |
| Test config | Click **[Test Connection]** on the config |

### Priority When Multiple Configs Exist

When a provider has multiple configurations:
1. The **default** configuration is used
2. You can override per-request in the Models page

---

## Testing Connections

Click **Test Connection** to verify your configuration:

| Result | Meaning |
|--------|---------|
| ✓ Success | Key is valid, provider accessible |
| ✗ Invalid API key | Check key format and value |
| ✗ Connection failed | Check URL, network, firewall |
| ✗ Model not available | Key valid but model access restricted |

Test uses inexpensive models (e.g., `gpt-3.5-turbo`, `claude-3-haiku`) to minimize cost.

---

## Migrating from Environment Variables

If you have existing API keys in `.env` or `docker.env`:

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

- Database keys take priority
- Environment variables serve as fallback
- Remove env vars if no longer needed

### Migration Banner Visibility

The migration banner only appears when:
- You have environment variables configured
- Those providers are **not** already in the database
- If all env providers are already migrated, the banner won't show

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

### Docker Secrets

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

---

## Key Priority Order

When provisioning AI models, Open Notebook checks:

```
1. Database (highest priority)
      ↓
2. Environment variable
      ↓
3. Not configured (model unavailable)
```

This allows database keys to override environment variables without removing them.

---

## Deleting Keys

1. Click the **Delete** button on the provider card
2. Confirm deletion
3. Key is removed from database

If an environment variable exists for that provider, it becomes active again after deletion.

---

## Troubleshooting

### Key Not Saving

| Symptom | Cause | Solution |
|---------|-------|----------|
| Save button disabled | Empty or invalid input | Enter a valid key |
| Error on save | Database connection issue | Check database status |
| Key not persisting | Browser storage issue | Clear cache, retry |

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

1. Check if key was saved (status indicator)
2. Check if environment variable exists
3. Verify key format matches provider requirements
4. Test connection to diagnose

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
- Default URL: `http://localhost:11434`
- Ensure Ollama server is running

### Azure OpenAI
- Endpoint format: `https://{resource-name}.openai.azure.com`
- API version format: `YYYY-MM-DD` or `YYYY-MM-DD-preview`
- Deployment names configured separately in Models page

---

## Related

- **[AI Providers](../5-CONFIGURATION/ai-providers.md)** — Detailed provider setup via environment variables
- **[Security](../5-CONFIGURATION/security.md)** — Password and encryption configuration
- **[Environment Reference](../5-CONFIGURATION/environment-reference.md)** — All configuration options
