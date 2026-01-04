# AI Context & RAG - How Open Notebook Uses Your Research

Open Notebook uses different approaches to make AI models aware of your research depending on the feature. This section explains **RAG** (used in Ask) and **full-content context** (used in Chat).

---

## The Problem: Making AI Aware of Your Data

### Traditional Approaches (and their problems)

**Option 1: Fine-Tuning**
- Train the model on your data
- Pro: Model becomes specialized
- Con: Expensive, slow, permanent (can't unlearn)

**Option 2: Send Everything to Cloud**
- Upload all your data to ChatGPT/Claude API
- Pro: Works well, fast
- Con: Privacy nightmare, data leaves your control, expensive

**Option 3: Ignore Your Data**
- Just use the base model without your research
- Pro: Private, free
- Con: AI doesn't know anything about your specific topic

### Open Notebook's Dual Approach

**For Chat**: Sends the entire selected content to the LLM
- Simple and transparent: You select sources, they're sent in full
- Maximum context: AI sees everything you choose
- You control which sources are included

**For Ask (RAG)**: Retrieval-Augmented Generation
- RAG = Retrieval-Augmented Generation
- The insight: *Search your content, find relevant pieces, send only those*
- Automatic: AI decides what's relevant based on your question

---

## How RAG Works: Three Stages

### Stage 1: Content Preparation

When you upload a source, Open Notebook prepares it for retrieval:

```
1. EXTRACT TEXT
   PDF → text
   URL → webpage text
   Audio → transcribed text
   Video → subtitles + transcription

2. CHUNK INTO PIECES
   Long documents → break into ~500-word chunks
   Why? AI context has limits; smaller pieces are more precise

3. CREATE EMBEDDINGS
   Each chunk → semantic vector (numbers representing meaning)
   Why? Allows finding chunks by similarity, not just keywords

4. STORE IN DATABASE
   Chunks + embeddings + metadata → searchable storage
```

**Example:**
```
Source: "AI Safety Research 2026" (50-page PDF)
↓
Extracted: 50 pages of text
↓
Chunked: 150 chunks (~500 words each)
↓
Embedded: Each chunk gets a vector (1536 numbers for OpenAI)
↓
Stored: Ready for search
```

---

### Stage 2: Query Time (What You Search For)

When you ask a question, the system finds relevant content:

```
1. YOU ASK A QUESTION
   "What does the paper say about alignment?"

2. SYSTEM CONVERTS QUESTION TO EMBEDDING
   Your question → vector (same way chunks are vectorized)

3. SIMILARITY SEARCH
   Find chunks most similar to your question
   (using vector math, not keyword matching)

4. RETURN TOP RESULTS
   Usually top 5-10 most similar chunks

5. YOU GET BACK
   ✓ The relevant chunks
   ✓ Where they came from (sources + page numbers)
   ✓ Relevance scores
```

**Example:**
```
Q: "What does the paper say about alignment?"
↓
Q vector: [0.23, -0.51, 0.88, ..., 0.12]
↓
Search: Compare to all chunk vectors
↓
Results:
  - Chunk 47 (alignment section): similarity 0.94
  - Chunk 63 (safety approaches): similarity 0.88
  - Chunk 12 (related work): similarity 0.71
```

---

### Stage 3: Augmentation (How AI Uses It)

Now you have the relevant pieces. The AI uses them:

```
SYSTEM BUILDS A PROMPT:
  "You are an AI research assistant.

   The user has the following research materials:
   [CHUNK 47 CONTENT]
   [CHUNK 63 CONTENT]

   User question: 'What does the paper say about alignment?'

   Answer based on the above materials."

AI RESPONDS:
  "Based on the research materials, the paper approaches
   alignment through [pulls from chunks] and emphasizes
   [pulls from chunks]..."

SYSTEM ADDS CITATIONS:
  "- See research materials page 15 for approach details
   - See research materials page 23 for emphasis on X"
```

---

## Two Search Modes: Exact vs. Semantic

Open Notebook provides two different search strategies for different goals.

### 1. Text Search (Keyword Matching)

**How it works:**
- Uses BM25 ranking (the same algorithm Google uses)
- Finds chunks containing your keywords
- Ranks by relevance (how often keywords appear, position, etc.)

**When to use:**
- "I remember the exact phrase 'X' and want to find it"
- "I'm looking for a specific name or number"
- "I need the exact quote"

**Example:**
```
Search: "transformer architecture"
Results:
  1. Chunk with "transformer architecture" 3 times
  2. Chunk with "transformer" and "architecture" separately
  3. Chunk with "transformer-based models"
```

### 2. Vector Search (Semantic Similarity)

**How it works:**
- Converts your question to a vector (number embedding)
- Finds chunks with similar vectors
- No keywords needed—finds conceptually similar content

**When to use:**
- "Find content about X (without saying exact words)"
- "I'm exploring a concept"
- "Find similar ideas even if worded differently"

**Example:**
```
Search: "what's the mechanism for model understanding?"
Results (no "understanding" in any chunk):
  1. Chunk about interpretability and mechanistic analysis
  2. Chunk about feature analysis
  3. Chunk about attention mechanisms

Why? The vectors are semantically similar to your concept.
```

---

## Context Management: Your Control Panel

Here's where Open Notebook is different: **You decide what the AI sees.**

### The Three Levels

| Level | What's Shared | Example Cost | Privacy | Use Case |
|-------|---------------|--------------|---------|----------|
| **Full Content** | Complete source text | 10,000 tokens | Low | Detailed analysis, close reading |
| **Summary Only** | AI-generated summary | 2,000 tokens | High | Background material, references |
| **Not in Context** | Nothing | 0 tokens | Max | Confidential, irrelevant, or archived |

### How It Works

**Full Content:**
```
You: "What's the methodology in paper A?"
System:
  - Searches paper A
  - Retrieves full paper content (or large chunks)
  - Sends to AI: "Here's paper A. Answer about methodology."
  - AI analyzes complete content
  - Result: Detailed, precise answer
```

**Summary Only:**
```
You: "I want to chat using paper A and B"
System:
  - For Paper A: Sends AI-generated summary (not full text)
  - For Paper B: Sends full content (detailed analysis)
  - AI sees 2 sources but in different detail levels
  - Result: Uses summaries for context, details for focused content
```

**Not in Context:**
```
You: "I have 10 sources but only want 5 in context"
System:
  - Paper A-E: In context (sent to AI)
  - Paper F-J: Not in context (AI can't see them, doesn't search them)
  - AI never knows these 5 sources exist
  - Result: Tight, focused context
```

### Why This Matters

**Privacy**: You control what leaves your system
```
Scenario: Confidential company docs + public research
Control: Public research in context → Confidential docs excluded
Result: AI never sees confidential content
```

**Cost**: You control token usage
```
Scenario: 100 sources for background + 5 for detailed analysis
Control: Full content for 5 detailed, summaries for 95 background
Result: 80% lower token cost than sending everything
```

**Quality**: You control what the AI focuses on
```
Scenario: 20 sources, question requires deep analysis
Control: Full content for relevant source, exclude others
Result: AI doesn't get distracted; gives better answer
```

---

## The Difference: Chat vs. Ask

**IMPORTANT**: These use completely different approaches!

### Chat: Full-Content Context (NO RAG)

**How it works:**
```
YOU:
  1. Select which sources to include in context
  2. Set context level (full/summary/excluded)
  3. Ask question

SYSTEM:
  - Takes ALL selected sources (respecting context levels)
  - Sends the ENTIRE content to the LLM at once
  - NO search, NO retrieval, NO chunking
  - AI sees everything you selected

AI:
  - Responds based on the full content you provided
  - Can reference any part of selected sources
  - Conversational: context stays for follow-ups
```

**Use this when**:
- You know which sources are relevant
- You want conversational back-and-forth
- You want AI to see the complete context
- You're doing close reading or analysis

**Advantages:**
- Simple and transparent
- AI sees everything (no missed content)
- Conversational flow

**Limitations:**
- Limited by LLM context window
- You must manually select relevant sources
- Sends more tokens (higher cost with many sources)

---

### Ask: RAG - Automatic Retrieval

**How it works:**
```
YOU:
  Ask one complex question

SYSTEM:
  1. Analyzes your question
  2. Searches across ALL your sources automatically
  3. Finds relevant chunks using vector similarity
  4. Retrieves only the most relevant pieces
  5. Sends ONLY those chunks to the LLM
  6. Synthesizes into comprehensive answer

AI:
  - Sees ONLY the retrieved chunks (not full sources)
  - Answers based on what was found to be relevant
  - One-shot answer (not conversational)
```

**Use this when**:
- You have many sources and don't know which are relevant
- You want the AI to search automatically
- You need a comprehensive answer to a complex question
- You want to minimize tokens sent to LLM

**Advantages:**
- Automatic search (you don't pick sources)
- Works across many sources at once
- Cost-effective (sends only relevant chunks)

**Limitations:**
- Not conversational (single question/answer)
- AI only sees retrieved chunks (might miss context)
- Search quality depends on how well question matches content

---

## What This Means: Privacy by Design

Open Notebook's RAG approach gives you something you don't get with ChatGPT or Claude directly:

**You control the boundary between:**
- What stays private (on your system)
- What goes to AI (explicitly chosen)
- What the AI can see (context levels)

### The Audit Trail

Because everything is retrieved explicitly, you can ask:
- "Which sources did the AI use for this answer?" → See citations
- "What exactly did the AI see?" → See chunks in context level
- "Is the AI's claim actually in my sources?" → Verify citation

This prevents hallucinations or misrepresentation better than most systems.

---

## How Embeddings Work (Simplified)

The magic of semantic search comes from embeddings. Here's the intuition:

### The Idea
Instead of storing text, store it as a list of numbers (vectors) that represent "meaning."

```
Chunk: "The transformer uses attention mechanisms"
Vector: [0.23, -0.51, 0.88, 0.12, ..., 0.34]
        (1536 numbers for OpenAI)

Another chunk: "Attention allows models to focus on relevant parts"
Vector: [0.24, -0.48, 0.87, 0.15, ..., 0.35]
        (similar numbers = similar meaning!)
```

### Why This Works
Words that are semantically similar produce similar vectors. So:
- "alignment" and "interpretability" have similar vectors
- "transformer" and "attention" have related vectors
- "cat" and "dog" are more similar than "cat" and "radiator"

### How Search Works
```
Your question: "How do models understand their decisions?"
Question vector: [0.25, -0.50, 0.86, 0.14, ..., 0.33]

Compare to all stored vectors. Find the most similar:
- Chunk about interpretability: similarity 0.94
- Chunk about explainability: similarity 0.91
- Chunk about feature attribution: similarity 0.88

Return the top matches.
```

This is why semantic search finds conceptually similar content even when words are different.

---

## Key Design Decisions

### 1. Search, Don't Train
**Why?** Fine-tuning is slow and permanent. Search is flexible and reversible.

### 2. Explicit Retrieval, Not Implicit Knowledge
**Why?** You can verify what the AI saw. You have audit trails. You control what leaves your system.

### 3. Multiple Search Types
**Why?** Different questions need different search (keyword vs. semantic). Giving you both is more powerful.

### 4. Context as a Permission System
**Why?** Not everything you save needs to reach AI. You control granularly.

---

## Summary

Open Notebook gives you **two ways** to work with AI:

### Chat (Full-Content)
- Sends entire selected sources to LLM
- Manual control: you pick sources
- Conversational: back-and-forth dialog
- Transparent: you know exactly what AI sees
- Best for: focused analysis, close reading

### Ask (RAG)
- Searches and retrieves relevant chunks automatically
- Automatic: AI finds what's relevant
- One-shot: single comprehensive answer
- Efficient: sends only relevant pieces
- Best for: broad questions across many sources

**Both approaches:**
1. Keep your data private (doesn't leave your system by default)
2. Give you control (you choose which features to use)
3. Create audit trails (citations show what was used)
4. Support multiple AI providers

**Coming Soon**: The community is working on adding RAG capabilities to Chat as well, giving you the best of both worlds.
