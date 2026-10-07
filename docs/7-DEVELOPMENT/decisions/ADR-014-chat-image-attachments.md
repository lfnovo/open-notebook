# ADR-014: Keep chat image attachments in the message checkpoint

- **Status**: Accepted
- **Date**: 2026-10-07
- **Related**: [ADR-002](ADR-002-external-libraries.md), [chat-effectively.md](../../3-USER-GUIDE/chat-effectively.md)

## Context

Notebook and source chats previously accepted only text. Users need to ask about screenshots, diagrams and photographs alongside their research context, and revisit those images in saved conversations.

## Decision

Both chat APIs accept an optional list of up to four inline images, each at most 5 MB, in PNG, JPEG or WebP format. Shared validation checks the actual file format, encoding and dimensions (at most 25 megapixels); external URLs and filesystem paths are not accepted. Text is optional when an image is attached.

Images become LangChain image content blocks in the human message. The existing Esperanto provisioning path supplies the selected model; providers interpret the image themselves. Filenames live in message metadata. Both image blocks and filenames persist in the existing SQLite checkpoint, so history and follow-up questions retain the attachments without a separate file store or database migration.

For automatic model selection, count text plus an estimated 2,048-token allowance per image, excluding base64 bytes. The provider determines the actual image token usage. Vision support remains a property of the selected model, and an unsupported-image error asks the user to select a model with vision support.

## Consequences

- Existing text-only requests remain supported. Message responses add an `images` list, empty for text-only messages.
- Attaching an image to chat does not create a source or require OCR/Docling. Source extraction remains delegated to Content Core.
- Checkpoint size and request size grow with attached images. Limits bound each turn, while conversation retention follows the existing checkpoint lifecycle.
- The composer supports file selection, paste and drop, previews/removal, and retains its draft if sending fails.
