# Notebooks, Sources, Insights, and Notes

Open Notebook has four kinds of content. Knowing how they relate explains most of the app.

```
NOTEBOOK  "AI Safety Research"  (name + description)
 │
 ├── SOURCES  (linked; a source can be linked to several notebooks)
 │    ├── safety_paper.pdf
 │    │     └── INSIGHTS  "Dense Summary", "Key Insights"   ← made by transformations
 │    └── alignment_talk.mp4
 │          └── INSIGHTS  "Simple Summary"
 │
 └── NOTES  (belong to this notebook)
      ├── My reading notes          (Human)
      └── Answer saved from chat    (AI Generated)
```

---

## Notebooks

A **notebook** is a workspace for one project or topic. It has a name, an optional description, its linked sources, its notes and its chat sessions.

- The **name and description are sent to the AI in notebook Chat** as project information, so a good description helps Chat answers. Ask, Search and transformations don't use them.
- Notebooks can be **archived** (hidden from the active list, nothing is deleted) and unarchived.
- **Deleting** a notebook permanently deletes its notes. Sources that are linked only to this notebook can be deleted too or kept in your library; sources shared with other notebooks are just unlinked. The delete dialog shows the counts before you confirm.

---

## Sources

A **source** is one piece of input material: an uploaded file, a web link or pasted text. See [Adding Sources](../3-USER-GUIDE/adding-sources.md) for the supported types.

When you add a source, a background job:

1. **Extracts the text** (document parsing, web page fetching, or speech-to-text for audio and video; see [Content Processing Engines](../3-USER-GUIDE/content-processing-engines.md)).
2. **Embeds it**, if embedding is enabled for that source: the text is split into chunks (about 400 tokens each by default) and each chunk gets a vector for semantic search.
3. **Runs the transformations** you selected, producing insights.

Things to know:

- **Sources live in a shared library.** The **Sources** page lists every source. A source can be linked to any number of notebooks (use **Add Existing Source** in a notebook) or to none. Removing a source from a notebook only unlinks it; deleting a source removes it everywhere.
- **The extracted text is not edited in the app.** To pick up a changed web page, use **Refresh content** on the source; to fix a bad upload, add the file again.
- **Search coverage depends on embedding.** Text (keyword) search works on every source. Vector search and Ask only see sources that have been embedded.

---

## Insights

An **insight** is the output of running a [transformation](../3-USER-GUIDE/transformations.md) on a source, for example a summary, a list of key points or a table of contents. Insights are the piece most people miss, and several features depend on them:

- **They are attached to the source**, not to a notebook. You see them on the source's **Insights** tab, labeled with the transformation's title.
- **They are the "Insights only" context level.** In notebook Chat, a source set to *Insights only* sends its title and its insights instead of its full text. A source with no insights can only be *Full content* or *Not included in chat*. See [AI Context & RAG](ai-context-rag.md#context-levels-in-notebook-chat).
- **They are the "Summary" option in podcasts.** When you pick content for an episode, *Summary* sends the source's insights.
- **They are searchable.** Text search, vector search and Ask all include insights.
- **They can be cited.** Chat answers can reference an insight, and clicking the reference opens it.
- **They can become notes**, but only through the API today (`POST /api/insights/{insight_id}/save-as-note`). The UI has no button for this.

You create insights when you add a source (step 3 of the Add Source wizard) or later from the source's Insights tab with **Generate New Insight**.

---

## Notes

A **note** is text that belongs to a notebook. A note has a title and Markdown content, and is marked either **Human** (you wrote it) or **AI Generated** (saved from the AI).

Ways to create one:

- **Write Note** in the notebook's Notes column.
- **Save to note** under a notebook Chat answer (one click; the title is generated for you).
- **Save to Notebooks** after an Ask answer (the question becomes the title, and you can pick several notebooks).

Notes are on or off in notebook Chat context (they have no insights level), are searchable, and are embedded for vector search when an embedding model is configured. See [Working with Notes](../3-USER-GUIDE/working-with-notes.md).

---

## How They Connect

```
Add source ──► extract text ──► embed (optional) ──► run transformations ──► insights
                                      │                                       │
                                      ▼                                       ▼
                         vector search + Ask                    "Insights only" context in Chat
                                                                "Summary" content in podcasts

Chat / Ask answer ──► Save to note / Save to Notebooks ──► note (AI Generated)
Write Note ──────────────────────────────────────────────► note (Human)
```

## Summary

| Concept | What it is | Belongs to |
|---------|------------|------------|
| **Notebook** | A project workspace with name and description | — |
| **Source** | Input material (file, link, text) | The library; linked to zero or more notebooks |
| **Insight** | A transformation's output for one source | One source |
| **Note** | Text you wrote or saved from the AI | One notebook |
