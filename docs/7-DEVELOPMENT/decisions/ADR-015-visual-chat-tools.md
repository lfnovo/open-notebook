# ADR-015: Visual tools for chat responses

## Status

Accepted.

## Context

Chats need to illustrate explanations with genuine source figures and generated
images. Text extraction loses the layout of scanned PDFs. Esperanto 2.28 exposes
language, embedding and speech modalities, but no image-generation interface.

## Decision

Add an explicit visual-response option to the two existing checkpointed chats.
Their language models are still provisioned through `provision_langchain_model`.
A shared asynchronous orchestrator binds four tools: page search, page preview,
source crop and image generation. PDFium renders original files; Pillow crops
normalized coordinates. Rendering is presentation of retained source assets,
not a replacement for Content Core's extraction/OCR pipeline. Serialize PDFium
access because its underlying library is not thread-safe.

Restrict file access to the upload directory and source IDs selected in the
current notebook, intersected with notebook membership, or the current source
in source chat. Require previewing a page before cropping it. Bound page search,
render dimensions, file sizes, tool rounds, attachments and image generations.

Keep provider SDK calls outside graph nodes in a small image-generation adapter.
This is a scoped exception to ADR-002 while Esperanto lacks this modality.
Prefer linked credentials, revalidate provider URLs and disable automatic API
retries to avoid duplicate generation charges. Support an operator-selected
image credential/model through environment settings. Never send credentials to
the frontend. Provider failures become sanitized tool results.

Save final image data and source/page provenance in AI message metadata, leaving
assistant text as text for compatibility with providers that reject assistant
image blocks. Page previews and tool internals remain transient. Both REST and
SSE expose images through the existing message image gallery and SQLite history.

For GPT-6, bind tools on a copied model using the Responses API, preserving the configured reasoning effort and transient encrypted reasoning context. See [ADR-016](ADR-016-exam-figures.md).

## Consequences

Visual mode requires a model with tool calling and vision. Generation additionally
requires an image-capable OpenAI-compatible account. Source crops require retained
original files; text-only and deleted-file sources cannot produce source images.
Inline images enlarge checkpoints, bounded by the existing 5 MB image limit.
The synchronous bridge exists only for the two legacy SqliteSaver chat graphs.
