# Frequently Asked Questions

Questions that aren't about an error message. For errors, see the [Troubleshooting index](index.md).

---

## General

### What is Open Notebook?

An open-source, self-hosted research assistant in the spirit of Google's NotebookLM: you collect sources into notebooks, chat with them, search them, run transformations that extract insights, and generate podcasts. You choose the AI providers, including fully local ones.

### How is it different from Google NotebookLM?

- **You host it.** Your notebooks, sources and notes stay in your own database.
- **You choose the models.** 24 providers are supported, from OpenAI and Anthropic to Ollama on your own machine. See [AI Providers](../5-CONFIGURATION/ai-providers.md).
- **It's open source.** You can read, change and extend it.

What leaves your machine is what you send to the AI providers you configure: when you chat, transform or generate a podcast, the relevant source content goes to that provider. When Ollama, LM Studio or Speaches runs on your own hardware, that content stays there; a remote endpoint receives it like any other provider.

### Can I use it offline?

Yes, with local models for everything: Ollama, LM Studio or oMLX for chat and embeddings, and [Speaches](../5-CONFIGURATION/local-tts.md) for speech. Adding web pages and YouTube videos still needs internet access, of course.

### What can I add as a source?

Files (PDF, Word, PowerPoint, Excel, EPUB, OpenDocument, HTML, plain text and Markdown; audio and video such as MP3, WAV, M4A and MP4; ZIP archives), web pages, YouTube videos and pasted text. Images and scanned documents need the optional Docling engine (`OPEN_NOTEBOOK_ENABLE_DOCLING=true`). Audio, video and YouTube videos without captions need a speech-to-text model. See [Adding Sources](../3-USER-GUIDE/adding-sources.md).

### How much does it cost?

The software is free. AI usage is billed by your providers per token, character or minute, at their prices; local models cost nothing beyond your hardware. The biggest cost drivers are the size of the context you send (how many sources are included in chat, and as "Full content" or "Insights only"), embedding large libraries, and podcast audio.

---

## AI models

### Which provider should I start with?

- **Simplest:** one provider that covers language, embeddings and speech, such as OpenAI or Google AI.
- **Many models with one key:** OpenRouter.
- **Private and free:** Ollama, plus Speaches for speech.

Providers like Anthropic only offer language models, so you'd add a second one for embeddings. The modality table is in [AI Providers](../5-CONFIGURATION/ai-providers.md#providers-and-what-they-offer).

### Can I mix providers?

Yes. Every model role is assigned separately under **Manage → Models → Default Model Assignments**: Chat, Transformation, Tools, Large Context, Embedding, Text-to-Speech and Speech-to-Text. You can also override the model for a single chat session.

### What happens if I change the embedding model?

Existing embeddings were made by the old model and won't match new searches. Open Notebook warns you and offers to go to the **Advanced** page to rebuild them. Rebuild before relying on search or Ask.

---

## Data

### Where is my data?

With the shipped `docker-compose.yml`, in two directories next to it:

- `./surreal_data`: the SurrealDB database (notebooks, sources' text, notes, chats, settings, encrypted credentials)
- `./notebook_data`: uploaded files, podcast audio and caches

The single-container setup uses `./surreal_single_data` for the database.

### How do I back up?

Stop the stack, archive both directories, start it again. Keep `OPEN_NOTEBOOK_ENCRYPTION_KEY` safe too: without it, the provider keys in a restored database can't be decrypted. Step-by-step: [Advanced → Backup & Restore](../5-CONFIGURATION/advanced.md#backup--restore).

Always back up before upgrading. Some upgrades can't be undone without a backup, such as the credential encryption change in v1.15.0.

### Can I sync between devices?

There is no built-in sync. Run one instance that all your devices reach over the network, or move data with backup and restore.

### What happens when I delete a notebook?

Deletion is permanent ("This action cannot be undone."). The notebook's notes are always deleted; you can choose to also delete sources that belong only to that notebook. Sources shared with other notebooks are kept. To put a notebook away without losing it, use **Archive** instead.

---

## Running it

### Can I use the API directly?

Yes. Interactive documentation is at `http://localhost:5055/docs`. When a password is set, send it as `Authorization: Bearer <password>`. See [Security → API client examples](../5-CONFIGURATION/security.md#api-client-examples) and the [API Reference](../7-DEVELOPMENT/api-reference.md).

### Is it ready for an internet-facing deployment?

It can run on a server, but its built-in protection is basic: one shared password, no user accounts, no rate limiting, and CORS open to all origins by default. Put it behind HTTPS, set a password, restrict `CORS_ORIGINS`, and keep the database private. See [Security](../5-CONFIGURATION/security.md) and [Reverse Proxy](../5-CONFIGURATION/reverse-proxy.md).

### How do I change a setting?

Infrastructure settings are environment variables in the `open_notebook` service's `environment:` block, applied with `docker compose up -d`. Everything else is in the UI. See [Configuration](../5-CONFIGURATION/index.md).

### How do I update?

Back up, then `docker compose pull && docker compose up -d`. Database migrations run automatically when the API starts.

---

## Getting help

- **Discord:** https://discord.gg/37XJPXfz2w
- **GitHub Discussions:** questions and ideas, https://github.com/lfnovo/open-notebook/discussions
- **GitHub Issues:** reproducible bugs, https://github.com/lfnovo/open-notebook/issues

When reporting a bug, include the exact error message, steps to reproduce, relevant logs (without keys or passwords), your version and how you run Open Notebook.

---

## Related

- [Quick Fixes](quick-fixes.md)
- [AI & Chat Issues](ai-chat-issues.md)
- [Processing Issues](processing-issues.md)
- [Connection Issues](connection-issues.md)
