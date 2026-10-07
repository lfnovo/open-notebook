# ADR-016: Shared figures for practice exams

## Status

Accepted

## Context

Practice questions can require interpreting a source chart or an educational illustration. Generating a question before obtaining its image risks referring to a missing figure or producing an answer key unrelated to the pixels. Duplicating encoded images in every question inflates responses and storage.

## Decision

An optional image preparation step runs before structured question generation, enabled by default. It reuses the bounded visual tools from [ADR-015](ADR-015-visual-chat-tools.md), restricted to sources used in the notebook study material. Prompts favor source crops, prohibit answer sheets and solved exercises, and allow generated illustrations when necessary. The preparation step may finish with no images.

The generator receives actual pixels and stable figure IDs. Questions reference up to two figures; unknown IDs invalidate a question. The exam stores a shared `images` pool and question `image_ids`; unused figures are discarded. The existing schemaless exam record needs no migration. Old records default to empty pools and references. Exam lists omit image bytes.

Taking an exam displays neutral figure captions. API responses suppress original captions and source provenance until answer-key review. Open-answer grading receives the exact saved figures used by the question. No images are regenerated during grading or review.

GPT-6 tool calls use LangChain's Responses transport with the configured reasoning effort, encrypted reasoning context and `store=false`. The original provisioned model is copied, preserving credentials and provider endpoints. This follows the [GPT-6 Luna tool compatibility requirements](https://developers.openai.com/api/docs/models/gpt-6-luna), which disallow reasoning with tools on Chat Completions. Other models retain their existing transport.

## Consequences

Visual preparation adds bounded tool/model work and possibly one image-generation charge. Vision and tool support are required when enabled; users can opt out for text-only models. Pedagogical relevance and scientific image accuracy remain model-dependent. Source crops and generated assets share existing validation and size limits.
