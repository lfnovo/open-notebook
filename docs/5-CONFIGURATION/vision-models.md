# Vision Models

Configure a default **Vision Model** to let Open Notebook extract content from images, PDF pages, and video frames using a multimodal LLM (GPT-4o, Claude 3+, Gemini, etc.).

> **What this unlocks**: image-only files (`.jpg`, `.png`, `.webp`, …) become a supported source type, PDFs get vision-based page analysis (useful for scans, diagrams, complex layouts), and videos get visual context combined with the existing audio transcript.

---

## How It Works

Vision support is delivered by two upstream libraries:

- **[Esperanto](https://github.com/lfnovo/esperanto)** ([PR #191](https://github.com/lfnovo/esperanto/pull/191)) — adds multimodal (image) input to `chat_complete` across all LLM providers. Open Notebook calls vision-capable LLMs through this unified surface.
- **[content-core](https://github.com/lfnovo/content-core)** ([PR #37](https://github.com/lfnovo/content-core/pull/37)) — adds vision-model–based extractors that render PDF pages with `pdftoppm`, sample video frames with `ffmpeg`, and feed them to the configured vision model.

Open Notebook wires the user's configured Vision Model (and its credential) through to content-core during source ingestion. When no Vision Model is set, the system falls back to the configured **Chat Model** — so any existing install with a multimodal chat model already gets vision support automatically.

---

## What Gets Vision-Processed

When a Vision Model (or fallback chat model) is configured:

| Source type | Default behavior | With vision model |
|---|---|---|
| **Images** (`image/*`) | Unsupported | Described directly by the vision model |
| **PDFs** | `pdfplumber` text extraction | Pages rendered to images and analyzed |
| **Videos** | Audio transcript only | Audio transcript + visual frame analysis |
| **Documents** (.docx, .pptx, …) | Unchanged | Unchanged (text extraction only) |
| **Web links** | Unchanged | Unchanged |

**Routing precedence** (handled by content-core):
- `document_engine="docling"` always wins.
- `document_engine="auto"` + Vision Model set → vision route for PDF / image / video MIME types.
- No Vision Model configured → standard text/audio pipeline (PDFs → pdfplumber, videos → audio-only, images → unsupported).

**Adaptive sampling** (avoids blowing up token cost on large inputs):

- **PDFs**: every page up to 20 → every 2nd up to 100 → every 5th up to 500 → every 10th beyond.
- **Videos**: 1.0 fps for ≤60 s → 0.5 fps for ≤5 min → 0.2 fps for ≤15 min → 0.1 fps beyond.
- Pages and frames are analyzed in parallel with a concurrency cap of 5.

---

## Configuration

### 1. Add a vision-capable provider credential

Any multimodal LLM works. Common choices:

| Provider | Recommended models |
|---|---|
| **OpenAI** | `gpt-4o`, `gpt-4o-mini` |
| **Anthropic** | `claude-sonnet-4-5`, `claude-3-5-sonnet`, `claude-3-5-haiku` |
| **Google** | `gemini-2.0-flash`, `gemini-1.5-pro` |
| **OpenRouter** | Any of the above by routed name |
| **Ollama** | `llava`, `llama3.2-vision`, `qwen2.5vl` |

Add the credential the usual way: **Settings → API Keys → Add Credential → Test Connection → Discover Models → Register Models**. See the [AI Providers Configuration Guide](ai-providers.md) for per-provider walkthroughs.

### 2. Set the default Vision Model

1. Go to **Settings → API Keys**.
2. Scroll to **Default Models**.
3. Pick a registered language model in the **Vision Model** dropdown.
4. Save.

The dropdown lists every registered language-type model — Open Notebook does not capability-detect, so make sure the model you pick actually accepts image input. Non-multimodal models will surface the provider's API error verbatim during ingestion.

> **Tip:** if you already use a multimodal model as your **Chat Model** (e.g. `gpt-4o`, `claude-sonnet-4-5`, `gemini-2.0-flash`), you can leave **Vision Model** empty — ingestion will fall back to the chat model.

### 3. (PDFs / videos only) Install system binaries

Vision PDF and video extraction shell out to standard tooling that must be on `PATH` inside the API container or host:

- `pdftoppm` (from **poppler**) — required for PDF page rendering.
- `ffmpeg` and `ffprobe` — required for video frame extraction.

The official Open Notebook Docker image ships these. If you run from source on macOS:

```bash
brew install poppler ffmpeg
```

Debian / Ubuntu:

```bash
apt-get install -y poppler-utils ffmpeg
```

Image-only ingestion does **not** need either binary.

---

## Behavior & Failure Modes

- **No vision model configured** — images remain unsupported; PDFs use `pdfplumber`; videos use audio-only. Existing behavior preserved.
- **Vision model fails on a frame/page** — the processor returns an `ExtractionOutput` with a placeholder message rather than aborting the whole source.
- **Video audio extraction fails** — the visual analysis still completes; the transcript portion is simply omitted.
- **Credential pass-through** — Open Notebook forwards the model's stored credential to content-core via `vision_config` (mirroring how speech-to-text credentials are passed). Models without an attached credential rely on environment-variable defaults at the provider level.

---

## Cost Considerations

Vision input is significantly more expensive than text. A 50-page scanned PDF rendered at full resolution can easily produce **5–15× the tokens** of the equivalent OCR-extracted text. Recommendations:

- Use **`gpt-4o-mini`**, **`claude-3-5-haiku`**, or **`gemini-2.0-flash`** as a default Vision Model for routine ingestion — quality is good enough for most diagrams/scans at a fraction of the cost of flagship models.
- Reserve flagship vision models (`gpt-4o`, `claude-sonnet-4-5`, `gemini-1.5-pro`) for sources where layout, handwriting, or detailed diagrams matter.
- For digital (text-native) PDFs, **leave Vision Model unset** or rely on `document_engine="docling"` — pdfplumber is faster and free.

---

## Troubleshooting

**"pdftoppm: command not found" / "ffmpeg: command not found"**
Install the binaries (see step 3) and restart the API. Image-only ingestion does not need either.

**Images upload but produce empty descriptions**
The selected Vision Model probably isn't multimodal. Re-select an image-capable model (see the table above) and retry.

**PDF processing times out on huge files**
Adaptive sampling already caps page rendering, but very large PDFs (500+ pages) at high concurrency can still hit provider rate limits. Use a cheaper / higher-throughput vision model, or split the PDF.

**Video has no visual analysis, only transcript**
Either no Vision Model is configured or `ffmpeg`/`ffprobe` is missing. Check the API logs for `Failed to retrieve model configuration` or ffmpeg errors.

---

## Related Docs

- [AI Providers Configuration](ai-providers.md) — per-provider credential setup
- [Adding Sources](../3-USER-GUIDE/adding-sources.md) — how source ingestion works end to end
- [Local STT](local-stt.md) — companion feature for audio/video transcription
