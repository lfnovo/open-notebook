# Video Understanding

Open Notebook can now enrich video sources with **provider-configurable visual analysis** in addition to transcript text.

---

## What This Feature Does

When a source is detected as a video and a default `video_understanding` model is configured, Open Notebook will:

1. extract the usual transcript/text content;
2. call the configured video-understanding provider;
3. normalize the provider response into a structured analysis artifact;
4. render that analysis back into Markdown so search, embeddings, and chat continue to work with the existing text-first pipeline.

If no video-understanding model is configured, the existing transcript-first behavior is preserved.

---

## Current Scope

The first implementation is intentionally conservative:

- it adds a new model type: `video_understanding`
- it adds a new default slot: `default_video_understanding_model`
- it stores structured video-analysis artifacts in `source_analysis`
- it currently supports **OpenAI-compatible** video-understanding endpoints as the first adapter

This was designed so provider support can expand without changing the ingestion architecture.

---

## How To Configure

### 1. Add a credential

Go to:

`Settings → API Keys → Add Credential`

For the current implementation, add an **OpenAI-Compatible** credential with:

- `Base URL`: your provider endpoint
- `API Key`: your provider key, if required

---

### 2. Register a video-understanding model

In the same Settings page:

1. open the provider's **Models** dialog
2. add or discover the model you want
3. set its type to `video_understanding`

For providers like Ark / Doubao, this is typically the endpoint or deployment name that exposes the video-understanding capability.

---

### 3. Set the default model

In:

`Settings → API Keys → Default Model Assignments`

choose a model for:

- `Video Understanding Model`

---

## Current Limitations

- The first adapter expects a **directly accessible remote video URL** for video-understanding calls.
- Local uploaded video files still fall back safely to the existing transcript-first flow if they cannot be sent to the provider directly.
- This feature enriches **source ingestion**. It does **not** yet add direct raw-video chat sessions or a timeline playback UI.

---

## Recommended Provider Shape

The current adapter targets **OpenAI-compatible Responses-style APIs** for video understanding.

That keeps the architecture provider-neutral while allowing vendors such as Ark / Doubao to be used as the first implementation target.
