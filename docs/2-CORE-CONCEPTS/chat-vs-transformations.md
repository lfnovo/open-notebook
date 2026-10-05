# Chat vs. Ask vs. Transformations - Which Tool for Which Job?

Open Notebook has several ways to put AI to work on your content. They differ in what content they use, whether you can follow up, and where the result goes.

| | Notebook Chat | Source Chat | Ask | Transformations |
|---|---|---|---|---|
| **Where** | Notebook page, Chat column | Source page | Ask and Search → Ask (beta) | Add Source wizard, or a source's Insights tab |
| **Input** | Sources and notes you put in context | One source (text + insights) | Vector search over embedded content | One source's full text |
| **Follow-ups** | Yes, in saved sessions | Yes, in saved sessions | No | No |
| **Output** | Chat answer with citations | Chat answer with citations | Answer with citations | An insight attached to the source |
| **Save it** | **Save to note** | Copy to clipboard | **Save to Notebooks** | Already saved as an insight |
| **Needs embeddings** | No | No | Yes | No |
| **Default model** | Chat Model | Chat Model | Chat Model (three stages) | Transformation Model, or the transformation's own model |

How each one gets its content is explained in [AI Context & RAG](ai-context-rag.md).

---

## Notebook Chat - Explore With Follow-Ups

Use Chat when you want a conversation about specific material: understanding a paper, comparing two reports, drafting from your sources. You decide what is in context with the per-source and per-note [context levels](ai-context-rag.md#context-levels-in-notebook-chat), and every message sends that content again.

Good for: close reading, comparing a handful of sources, iterating on an answer.
Not good for: questions across hundreds of sources (context gets too large) or finding which source mentions something (use Search or Ask).

→ [Chat Effectively](../3-USER-GUIDE/chat-effectively.md)

## Source Chat - Talk to One Source

Each source has its own chat on its page. It always uses that source's text and insights, so there is nothing to configure. Long sources are truncated to fit about 50,000 tokens.

## Ask - One Question Across Everything

Use Ask when you don't know which sources hold the answer. A strategy model plans searches, each search retrieves matching chunks, and a final model writes one answer with citations. It searches your whole knowledge base unless you limit it to specific notebooks, and it only sees embedded content.

Good for: questions across many sources, "what do my sources say about X".
Not good for: follow-up conversations, or content that isn't embedded.

→ [Search and Ask](../3-USER-GUIDE/search.md)

## Transformations - The Same Prompt, Saved as an Insight

A transformation is a saved prompt (for example "Dense Summary" or "Table of Contents") that runs on one source and stores the result as an **insight** on that source. You pick transformations when you add sources, or run one later from the source's Insights tab. Insights then feed Chat's *Insights only* level and the *Summary* option in podcasts.

There is no batch action for existing sources in the UI: to apply a transformation to many sources, select it in the Add Source wizard when you add them (batch uploads apply the same transformations to every item), or run it on each source.

Good for: consistent summaries or extractions across sources, making sources cheaper to chat with.
Not good for: one-off questions (use Chat or Ask).

→ [Transformations](../3-USER-GUIDE/transformations.md)

---

## Decision Guide

```
Do you know which sources matter?
├─ Yes → Do you want a conversation?
│        ├─ Yes → Notebook Chat (or Source Chat for a single source)
│        └─ No, the same extraction for each source → Transformation
└─ No  → Do you want an AI answer?
         ├─ Yes → Ask
         └─ No, just find the passages → Search (text or vector)
```

## Combining Them

A common flow:

1. Add sources with a summary transformation selected (Dense Summary is pre-selected on new installs).
2. Use **Ask** to find which sources address your question.
3. Open the notebook and **Chat** with those sources, using *Insights only* for background sources and *Full content* for the ones you are reading closely.
4. **Save to note** the answers worth keeping.
