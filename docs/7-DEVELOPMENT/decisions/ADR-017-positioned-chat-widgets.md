# ADR-017: Positioned images and interactive practice in chat

## Status

Accepted

## Context

A separate attachment gallery cannot express which paragraph a figure illustrates. Practice questions written as plain Markdown cannot be answered or graded inside the conversation. Notebook and source chat must retain existing provider support and checkpoint history.

## Decision

Visual tools return numbered attachments. The assistant inserts `[[image:N]]` at the relevant point in its final response. Only actual validated attachment indexes resolve; invented image URLs are removed. Historical attachments without markers still display once.

Both chat prompts support a `chat-quiz` JSON block when practice is requested or pedagogically useful. This structured response protocol requires no extra provider tool support or additional generation call for text tests. The backend validates one test with one to five questions, resolves references to actual figures, stores its private answer key in `chat_quiz`, and replaces the block with a positioned quiz marker. It never exposes the raw block in the API or checkpointed assistant text. Malformed/incomplete tests receive a bounded repair through the selected chat model with structured output. Repair preserves the original question material and available figure pixels. If repair fails, valid questions can still be retained; otherwise the explanation and figures remain visible with a localized notice. Raw test blocks and private keys are removed in all paths. Database persistence errors still propagate.

Quiz IDs are transmitted in separate message metadata. The frontend resolves only IDs present in this metadata and renders native interactive components in place, preserving prose and citations. Answer input and grading reuse the practice-exam components and service. Submitting stores a `chat_quiz_attempt`; grading receives the exact saved question figures. The answer key and original figure provenance become available after an attempt. Results survive chat reloads, and students can retake the test. Submit mutations never retry automatically.

Migration 27 defines the quiz and attempt tables and indexes. Quizzes belong to a chat session; deleting that session removes its quizzes and attempts. Practice exams remain separate from these contextual tests.

## Consequences

Automatic practice selection depends on the model following the prompt. Visual tests require the existing visual-response option for obtaining new figures. Text tests work with ordinary chat models. The protocol and metadata remain transient model instructions and persisted application data; they are rendered as UI widgets rather than shown as implementation syntax.

Explicit requests in the latest human message activate visual tools independently of the composer toggle. Exam and questionnaire requests require an interactive card; a missing quiz block triggers bounded structured conversion using the current source context. Plain exam drafts are replaced before returning them so their answer keys cannot leak.
