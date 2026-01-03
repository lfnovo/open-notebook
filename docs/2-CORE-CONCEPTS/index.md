# Core Concepts - Understand the Mental Model

Before diving into how to use Open Notebook, it's important to understand **how it thinks**. These core concepts explain the "why" behind the design.

## The Five Mental Models

### 1. [Notebooks, Sources, and Notes](notebooks-sources-notes.md)
How Open Notebook organizes your research. Understand the three-tier container structure and how information flows from raw materials to finished insights.

**Key idea**: A notebook is a scoped research container. Sources are inputs (PDFs, URLs, etc.). Notes are outputs (your insights, AI-generated summaries, captured responses).

---

### 2. [AI Context & RAG](ai-context-rag.md)
How Open Notebook makes AI aware of your research without uploading everything to the cloud.

**Key idea**: RAG (Retrieval-Augmented Generation) means the AI searches your content, finds relevant pieces, and answers based on what it found. You control which content is in scope.

---

### 3. [Chat vs. Transformations](chat-vs-transformations.md)
Why Open Notebook has different interaction modes and when to use each one.

**Key idea**: Chat is conversational exploration (you control context). Transformations are batch processing (you define the template). They answer different questions.

---

### 4. [Context Management](chat-vs-transformations.md#context-management-the-control-panel)
Your control panel for privacy and cost. Decide what data actually reaches AI.

**Key idea**: You choose three levels—not in context (private), summary only (condensed), or full content (complete access). This gives you fine-grained control.

---

### 5. [Podcasts Explained](podcasts-explained.md)
Why Open Notebook can turn research into audio and why this matters.

**Key idea**: Podcasts transform your research into a different consumption format. Instead of reading, someone can listen and absorb your insights passively.

---

## Read This Section If:

- **You're new to Open Notebook** — Start here to understand how the system works conceptually before learning the features
- **You're confused about RAG** — Section 2 explains what it is and why it matters
- **You're wondering when to use Chat vs Ask** — Section 3 clarifies the differences
- **You want to understand privacy controls** — Section 4 shows you what you can control
- **You're curious about podcasts** — Section 5 explains the architecture and why it's different from competitors

---

## The Big Picture

Open Notebook is built on a simple insight: **Your research deserves to stay yours**.

That means:
- **Privacy by default** — Your data doesn't leave your infrastructure unless you explicitly choose
- **AI as a tool, not a gatekeeper** — You decide which sources the AI sees, not the AI deciding for you
- **Flexible consumption** — Read, listen, search, chat, or transform your research however makes sense

These core concepts explain how that works.

---

## Next Steps

1. **Just want to use it?** → Go to [User Guide](../3-USER-GUIDE/index.md)
2. **Want to understand it first?** → Read the 5 sections above (15 min)
3. **Setting up for the first time?** → Go to [Installation](../1-INSTALLATION/index.md)

