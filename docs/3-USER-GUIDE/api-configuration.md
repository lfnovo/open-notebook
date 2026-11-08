# API Configuration

Connect AI providers and choose your default models in **Manage → Models**. API keys are stored encrypted in the database; no file editing is needed after the encryption key is set.

The page has three parts, top to bottom:

1. **Environment Variables Detected** banner (only if you have provider keys in environment variables; see [Migrating from Environment Variables](#migrating-from-environment-variables)).
2. **Default Model Assignments**: which model each feature uses.
3. **Provider sections**: one per provider, each showing *Configured* or *Not configured*, its configurations and their models.

---

## Encryption Setup

Storing API keys requires `OPEN_NOTEBOOK_ENCRYPTION_KEY`. Until it is set, the Models page shows **Encryption key not configured** and configurations can't be saved.

Set it on the `open_notebook` service in your `docker-compose.yml`:

```yaml
services:
  open_notebook:
    environment:
      - OPEN_NOTEBOOK_ENCRYPTION_KEY=<your-generated-secret>
```

Replace `<your-generated-secret>` with a long random secret that you generate yourself. Don't copy an example value from any guide. Either of these prints a suitable value:

```bash
openssl rand -hex 32                                   # macOS, Linux
```

```powershell
[guid]::NewGuid().ToString("N") + [guid]::NewGuid().ToString("N")   # Windows PowerShell
```

Apply the change by recreating the container (`docker compose up -d`).

> **Keep this value safe and stable.** If it changes, stored API keys can't be decrypted and their cards show **Decryption Error** until you restore the original value. If the original value is lost, the stored keys can't be recovered: delete those configurations and add them again.

Both `OPEN_NOTEBOOK_ENCRYPTION_KEY` and `OPEN_NOTEBOOK_PASSWORD` also accept a `_FILE` variant (for example `OPEN_NOTEBOOK_ENCRYPTION_KEY_FILE=/run/secrets/encryption_key`) for Docker secrets. For the encryption scheme, upgrading stored keys and backups, see [Security](../5-CONFIGURATION/security.md).

---

## Connect a Provider

The step-by-step setup (**Add Configuration** → **Test Connection** → **Discover Models** dialog → **Add (N)** → **Auto-assign Defaults** → a first chat) is in [AI Providers → Connect a provider](../4-AI-PROVIDERS/index.md#connect-a-provider). In short: add a configuration for the provider, test it, open its **Discover Models** dialog (the *Sync Models* button), pick a **Model Type**, tick the models (or type a name that isn't listed) and click **Add (N)**. Repeat per model type you need.

The models then appear under the configuration, each with a **Test Model** icon (sends a small request to that model) and a delete icon.

Which providers offer which model types (language, embedding, speech) is listed in [AI Providers](../4-AI-PROVIDERS/index.md); provider-specific setup notes are in [AI Providers configuration](../5-CONFIGURATION/ai-providers.md), [Ollama](../5-CONFIGURATION/ollama.md), [OpenAI-compatible](../5-CONFIGURATION/openai-compatible.md) and [oMLX](../5-CONFIGURATION/omlx.md).

> Several providers only offer language models. Ask and vector search also need an embedding model; podcasts need a text-to-speech model; uploaded audio and video files, and YouTube videos without a transcript, need a speech-to-text model. These can come from a different provider.

### Multiple configurations per provider

A provider can have several configurations, for example two API keys or two Ollama servers. Each model is linked to the configuration it was added from and uses that configuration's key and URL.

---

## Default Model Assignments

This section decides which model each feature uses. Fields marked with an asterisk are required.

| Assignment | Used for | If not set |
|------------|----------|-----------|
| **Chat Model** * | Notebook chat, source chat; the default for all three Ask stages on the Ask page | Chat and Ask fail |
| **Embedding Model** * | Embedding sources, notes and insights; vector search; Ask | Ask and vector search are unavailable |
| **Transformation Model** | Transformations (insights), titles for AI-generated notes | Uses the Chat Model |
| **Tools Model** | Ask, when called through the API without explicit models | Uses the Chat Model |
| **Large Context Model** | Any prompt over about 105,000 tokens | Uses the Chat Model |
| **Text-to-Speech Model** | Nothing at the moment: podcasts take their voice model from the speaker profile | — |
| **Speech-to-Text Model** | Transcribing uploaded audio and video files, and YouTube videos without a transcript | Those sources can't be transcribed (YouTube videos with a transcript still work) |

While the Chat Model or Embedding Model is missing, a notice offers **Auto-assign Defaults**, which fills those two from the models you have added (the other slots stay as they are). If it says *No models available to assign*, add some models first.

Podcasts use the models set in their episode and speaker profiles, not these defaults (see [Creating Podcasts](creating-podcasts.md)).

**Changing the Embedding Model** opens a confirmation: existing embeddings were made by the old model and won't match new queries. Choose **Change & Go to Rebuild** to go to **Advanced → Rebuild Embeddings**, or **Change Model Only** to rebuild later.

---

## Migrating from Environment Variables

If provider API keys are set as environment variables (the older way), the Models page shows **Environment Variables Detected**.

1. Click **Migrate to Database**.
2. For each provider that has keys in the environment and **no** configuration in the database yet, a configuration is created from those keys (encrypted). Providers that already have a configuration are skipped.
3. The environment variables are not changed. Once the migrated configurations work, you can remove the keys from your environment. Keep `OPEN_NOTEBOOK_ENCRYPTION_KEY`.

---

## Edit or Delete a Configuration

- **Edit** (pencil icon): change the name, URL or other fields. Leave **API Key** blank to keep the stored key.
- **Delete** (trash icon): if the configuration has models, you can pick another configuration of the same provider under **Migrate models to** and click **Migrate & Delete**, or click **Delete with Models** to remove the models too. Check **Default Model Assignments** afterwards if any of them used the deleted models.

---

## Troubleshooting

| Symptom | What to check |
|---------|---------------|
| Can't save a configuration, *Encryption key not configured* | Set `OPEN_NOTEBOOK_ENCRYPTION_KEY` and recreate the container |
| **Decryption Error** on a configuration | The encryption key changed. Restore the original value; if it's lost, delete the configuration and add it again |
| Test Connection fails | The key, the Base URL (from Docker, `localhost` means the container itself), firewall or proxy |
| A model isn't in Discover Models | Type its exact name in the search box and add it |
| *Missing required models* warning | Set the Chat Model and Embedding Model, or click **Auto-assign Defaults** |

More in [Troubleshooting](../6-TROUBLESHOOTING/index.md).
