# Search and Ask - Finding What You Need

Search and Ask live on the **Ask and Search** page (sidebar, under **Process**). Both work across your whole knowledge base, or only the notebooks you pick. There is no separate search box inside a notebook.

You can also start either from **Quick actions** (**Ctrl+K** / **⌘K**): type a query and choose *Search results for "..."* or *Ask about "..."*.

| | Search | Ask (beta) |
|---|---|---|
| **Gives you** | A list of matching sources, insights and notes | One written answer with citations |
| **Uses an AI model** | Vector search uses the embedding model; text search uses none | Embedding model plus a language model for each stage |
| **Best for** | Finding a passage, term or document | Questions whose answer is spread across sources |

How both work under the hood is explained in [AI Context & RAG](../2-CORE-CONCEPTS/ai-context-rag.md#search-text-vs-vector).

---

## Search

1. Open **Ask and Search** and choose the **Search** tab.
2. Type your query and press **Enter**.
3. Adjust if needed:
   - **Search Type**: **Text Search** or **Vector Search**.
   - **Search In**: **Search Sources** and/or **Search Notes**.
   - **Notebooks**: pick notebooks to limit the search, or leave all unchecked to search everything.

Results show how many were found; click a result to open the source, note or insight. Where available, a result also lists its **Matches** (the matching passages).

### Text Search vs. Vector Search

| | Text Search | Vector Search |
|---|---|---|
| **Matches** | Exact words (with English stemming) | Meaning, by similarity |
| **Covers** | Source titles and content, insights, note titles and content | Source content, insights, note content (not titles) |
| **Needs** | Nothing | An Embedding Model, and only finds embedded content |
| **Use when** | You know the term, name or phrase | You know the idea but not the wording |

If no Embedding Model is set, the page says *Vector search requires an embedding model. Only text search is available.*

**Tips:**
- Text search works best with distinctive words: names, acronyms, technical terms.
- Vector search works best with a descriptive phrase ("risks of relying on a single supplier") rather than one word.
- A source you can find with text search but not vector search probably isn't embedded. Open it and use **Embed Content**.

---

## Ask

1. Open **Ask and Search** and stay on the **Ask (beta)** tab.
2. Type your question.
3. Optionally limit it to some **Notebooks** (leave all unchecked for your whole knowledge base).
4. Press **Cmd/Ctrl+Enter** or click **Ask**.

While it runs, you'll see the stages as they finish:

- **Strategy**: the model's reasoning and the **Search Terms** it chose (up to five searches).
- **Individual Answers**: one partial answer per search, based on the top matches.
- **Final Answer**: the combined answer, with links to the cited items.

Click **Save to Notebooks** to keep the answer as a note (titled with your question) in one or more notebooks.

### Requirements

- **An Embedding Model** must be set. Without one, the Ask tab says *You can't use this feature because you have no embedding model selected.*
- **A Chat Model** must be set; it is used for all three stages by default.
- Ask only sees **embedded** content (sources added with embedding enabled, notes and insights).

### Choosing models

The tab shows **Using Default Models** or **Using Custom Models**. Click **Advanced** to open **Advanced Model Selection** and choose a **Strategy Model**, **Answer Model** and **Final Answer Model**, then **Save Changes**. The strategy step needs a model that reliably returns structured output; if it fails with *The strategy model returned no search terms for this question...*, pick a different Strategy Model or rephrase.

### When to use Ask

- Use Ask when you don't know which sources contain the answer.
- Ask is single-turn. To follow up, open a notebook and use [Chat](chat-effectively.md) with the sources Ask cited.
- Answers come only from matched chunks, so they can miss context that is spread thinly across a document. For close reading, use Chat with *Full content*.

---

## Troubleshooting

| Problem | Try |
|---------|-----|
| No results in vector search or Ask | Check that an Embedding Model is set and the sources are embedded; rebuild from **Advanced → Rebuild Embeddings** if you changed the embedding model |
| Text search misses a word | Try another form of the word or a synonym; stemming is English-only |
| Too many results | Limit to specific notebooks, or turn off **Search Sources** or **Search Notes** |
| Ask answer is empty or fails | Pick other models under **Advanced**; reasoning models with small output limits can return nothing |
