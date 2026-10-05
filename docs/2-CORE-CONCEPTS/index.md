# Core Concepts - Understand the Mental Model

These pages explain how Open Notebook is organized and how its AI features decide what content to use. Read them once and the rest of the app will make sense. For step-by-step instructions, go to the [User Guide](../3-USER-GUIDE/index.md).

## The Pages

### 1. [Notebooks, Sources, Insights, and Notes](notebooks-sources-notes.md)
The four things you work with.

**Key idea**: A notebook groups sources and notes for one project. Sources are your input material and can belong to several notebooks. Transformations turn a source into **insights**, which stay attached to the source. Notes are what you write or save from the AI.

---

### 2. [AI Context & RAG](ai-context-rag.md)
How each AI feature gets your content, and how you control it.

**Key idea**: **Chat** sends the sources and notes you put in context, with no searching. **Ask** searches your knowledge base (vector search) and answers from what it finds. Each source in a notebook has three context levels for Chat: *Not included in chat*, *Insights only* and *Full content*.

---

### 3. [Chat vs. Ask vs. Transformations](chat-vs-transformations.md)
Which tool to use for which job.

**Key idea**: Chat is a conversation over content you pick. Ask is a one-shot question over everything (or the notebooks you pick). Transformations run a saved prompt over one source and save the result as an insight.

---

### 4. [Podcasts Explained](podcasts-explained.md)
How a podcast episode is generated from your content.

**Key idea**: An outline model and a transcript model write a script from the content you select, then a text-to-speech model voices it. Episode profiles and speaker profiles hold the settings.

---

## The Big Picture

- **You choose the providers.** Open Notebook works with cloud and local AI providers. Content leaves your machine only when you use a cloud provider, and then only the content each feature sends (described in the pages above).
- **You choose what the AI sees.** In Chat you set the context per source and note. Ask and Search can be limited to specific notebooks.
- **Everything is stored in your own database.** Sources, insights, notes, chat history and podcasts live in your SurrealDB instance.

## Next Steps

- **Ready to use it?** Go to the [User Guide](../3-USER-GUIDE/index.md)
- **Not installed yet?** Go to [Installation](../1-INSTALLATION/index.md)
