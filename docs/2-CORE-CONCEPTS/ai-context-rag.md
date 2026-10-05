# AI Context & RAG - How Open Notebook Uses Your Research

An AI model only knows what is sent to it in the prompt. Open Notebook has two ways of getting your research into that prompt:

- **Chat** sends the content you selected, as it is. Nothing is searched.
- **Ask** searches your knowledge base and sends only the matching pieces. This is retrieval-augmented generation (RAG).

This page explains both, the context levels that control Chat, and the search that powers Ask.

---

## Context Levels in Notebook Chat

In a notebook, every source and note has a context level that decides what notebook Chat sends to the model.

| Level | Applies to | What is sent |
|-------|-----------|--------------|
| **Not included in chat** | Sources and notes | Nothing |
| **Insights only** | Sources that have insights | The source title and its [insights](notebooks-sources-notes.md#insights) |
| **Full content** | Sources and notes | Sources: title, insights and the full extracted text. Notes: title and content |

How it behaves:

- **Insights only needs insights.** It is offered only for sources that already have at least one insight. Run a transformation on a source to make it available.
- **Defaults when you open a notebook:** sources with insights start as *Insights only*, sources without insights start as *Full content*, and all notes are included.
- **Selections are not saved.** They live in the page and reset when you reload it.
- **The chat shows the total.** Above the message box, the chat panel shows how many sources and notes are in context and an estimated token and character count.

How to change it is described in [Chat Effectively](../3-USER-GUIDE/chat-effectively.md#choosing-what-the-ai-sees).

**Why it matters:**

- **Cost and speed.** Everything in context is sent with every message. *Insights only* is usually a fraction of the size of the full text.
- **Focus.** Leaving out unrelated sources gives the model less to get confused by.
- **What a cloud provider receives.** A source set to *Not included in chat* is not sent by Chat.

> **Context levels only apply to notebook Chat.** Ask, Search and podcast generation have their own selection (described below). A source excluded from Chat can still reach the model through Ask if it is embedded and Ask is not limited to other notebooks.

---

## Chat: Full Content, No Retrieval

When you send a message in notebook Chat, Open Notebook builds one prompt from:

1. the notebook's name and description,
2. every source and note in context, at its context level,
3. the conversation so far, and your new message.

There is no search step: the model sees all of the selected content every time. This is why Chat is good for reading closely and comparing a few sources, and why large selections get expensive.

The model is your **Chat Model** default, or the model you picked for that chat session. If the prompt is larger than about 105,000 tokens, Open Notebook switches to the **Large Context Model** default instead (or the Chat Model if none is set), even if you picked a model for the session.

### Source Chat

Opening a source and using its chat (**Chat with Sources** on the source view) is a separate chat about that single source. It sends the source's full text and its insights, trimmed to fit a budget of about 50,000 tokens. Longer sources are truncated, with a notice to the model that the text was cut.

---

## Ask: Retrieval Over Your Knowledge Base

Ask (on the **Ask and Search** page) answers one question in three stages:

```
Your question
    │
    ▼
1. STRATEGY      a model plans up to 5 searches
    │
    ▼
2. ANSWERS       each search runs a vector search (top 10 matches)
    │            and a model writes a partial answer from those matches
    ▼
3. FINAL ANSWER  a model combines the partial answers, with citations
```

Things to know:

- **Ask needs an embedding model.** Without a default Embedding Model the page tells you to set one up and Ask is unavailable.
- **Ask only sees embedded content.** It searches source chunks, insights and notes that have embeddings. A source added with embedding turned off is invisible to Ask until you embed it.
- **Ask searches everything by default.** Leave the **Notebooks** selector empty to search your whole knowledge base, or pick notebooks to limit it. Chat context levels don't apply.
- **Three model slots.** Strategy, Answer and Final Answer use your Chat Model default unless you change them under **Advanced** on the Ask tab.
- **Ask is single-turn.** There are no follow-ups. Save a useful answer with **Save to Notebooks**, or take the topic to Chat.

---

## Search: Text vs. Vector

The **Search** tab lets you find content yourself, without an AI answer. Both modes cover sources, insights and notes; you can turn sources or notes off and limit the search to specific notebooks.

### Text search (keywords)

- Full-text search with BM25 ranking.
- Matches source titles and content, insights, and note titles and content.
- Works on every source, embedded or not, and needs no AI model.
- Words are stemmed with an English stemmer (so "running" also matches "run"). Matching in other languages is less forgiving.

Use it for exact names, terms and phrases you remember.

### Vector search (meaning)

- Your query is turned into a vector with the embedding model and compared with the stored chunk vectors.
- Matches source content, insights and note content by similarity. Titles are not matched.
- Needs an embedding model, and only finds embedded content.

Use it when you know the idea but not the wording.

### How embedding works

When a source is embedded, its text is split into chunks of about 400 tokens with a 15% overlap (configurable with `OPEN_NOTEBOOK_CHUNK_SIZE` and `OPEN_NOTEBOOK_CHUNK_OVERLAP`), and each chunk is stored with its vector. Whether new sources are embedded is set by **Settings → Embedding and Search → Default Embedding Option** (Ask, Always or Never) and the checkbox in the Add Source wizard. If you change the embedding model, rebuild the embeddings from **Advanced → Rebuild Embeddings**; vectors from different models can't be compared.

---

## Citations

Chat and Ask answers cite the items they used by record ID, for example `[source:abc123]`, `[note:def456]` or `[insight:ghi789]`. The app shows these as clickable references that open the cited source, note or insight. Citations point to the whole item, not to a page or passage. See [Citations](../3-USER-GUIDE/citations.md).

---

## Privacy: What Leaves Your Machine

Content is sent to whichever provider runs the model for that feature. If all your models are local (for example Ollama), nothing leaves your machine. With a cloud provider:

| Feature | What the provider receives |
|---------|----------------------------|
| Notebook Chat | Notebook name and description, the sources and notes in context, the conversation |
| Source Chat | That source's text (up to the budget) and insights, the conversation |
| Ask | Your question, then the matching chunks, insights and notes from each search |
| Embedding | The text of every chunk, note and insight being embedded |
| Transformations | The full text of the source being transformed |
| Podcasts | See [Podcasts Explained](podcasts-explained.md#privacy-what-each-model-sees) |

You can mix providers, for example a local embedding model with a cloud chat model.

---

## Summary

| | Chat | Ask |
|---|---|---|
| **How content is chosen** | You set context levels per source and note | Vector search picks matching chunks |
| **Scope** | The current notebook | Whole knowledge base, or the notebooks you pick |
| **Needs embeddings** | No | Yes |
| **Conversation** | Multi-turn, saved in sessions | One question, one answer |
| **Best for** | Close reading and comparison of chosen sources | Questions across a lot of material |
