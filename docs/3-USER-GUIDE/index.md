# User Guide - How to Use Open Notebook

Step-by-step instructions for each feature. If you want to understand how things work first (notebooks, sources, insights, context levels), read [Core Concepts](../2-CORE-CONCEPTS/index.md).

---

## Before You Start

Open Notebook needs at least one AI provider and default models. In **Manage → Models**, add a provider configuration, sync its models, and set the **Default Model Assignments** (or click **Auto-assign Defaults**). Without a Chat Model and an Embedding Model, chat, transformations, Ask and vector search won't work. See [API Configuration](api-configuration.md).

---

## The Guides

| Guide | What it covers |
|-------|----------------|
| [Interface Overview](interface-overview.md) | The sidebar, the notebook page, the source view, keyboard shortcuts |
| [API Configuration](api-configuration.md) | Connecting AI providers, syncing models, default model assignments |
| [Adding Sources](adding-sources.md) | The Add Source wizard, file types, processing status, failures |
| [Content Processing Engines](content-processing-engines.md) | How files and URLs are extracted (Docling, Firecrawl, Jina, Crawl4AI, OCR) |
| [Transformations](transformations.md) | Generating insights from sources, built-in and custom transformations |
| [Chat Effectively](chat-effectively.md) | Notebook chat, context levels, sessions, model choice, source chat |
| [Citations](citations.md) | Reading and checking the references in AI answers |
| [Working with Notes](working-with-notes.md) | Writing notes and saving AI answers |
| [Search and Ask](search.md) | Text and vector search, and Ask across your knowledge base |
| [Creating Podcasts](creating-podcasts.md) | Generating episodes, episode and speaker profiles |

---

## Your First 15 Minutes

1. **Create a notebook.** Sidebar **New → Notebook** (or **Notebooks → New Notebook**). Give it a name and a short description; the description is sent to the AI in notebook Chat.
2. **Add a source.** In the notebook, **Add Source → Add Source**, then choose **Add URL**, **Upload File** or **Enter Text**. On the Process step, keep the pre-selected transformation and embedding, and click **Done**. Processing runs in the background; the card shows **Queued**, **Processing**, then **Completed**. See [Adding Sources](adding-sources.md).
3. **Chat.** In the Chat column, type a question and press **Ctrl+Enter** (**⌘+Enter** on Mac). Click a numbered reference in the answer to open what it cites.
4. **Keep the answer.** Click the **Save to note** icon under the answer. It appears in the Notes column.
5. **Ask across everything.** Open **Ask and Search**, stay on **Ask (beta)**, type a question and click **Ask**. Save the answer with **Save to Notebooks**.

---

## Which Feature for Which Task?

| Task | Use |
|------|-----|
| Explore a few sources with follow-up questions | [Notebook Chat](chat-effectively.md) |
| Ask one question across everything | [Ask](search.md#ask) |
| Find a passage or term you remember | [Text search](search.md#search) |
| Find content about an idea, whatever the wording | [Vector search](search.md#search) |
| Get the same summary or extraction for each source | [Transformations](transformations.md) |
| Listen to your research | [Podcasts](creating-podcasts.md) |

---

## Getting Help

- **Something fails or shows an error?** → [Troubleshooting](../6-TROUBLESHOOTING/index.md)
- **How does it work?** → [Core Concepts](../2-CORE-CONCEPTS/index.md)
- **Not installed yet?** → [Installation](../1-INSTALLATION/index.md)
