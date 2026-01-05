# Search Effectively - Finding What You Need

Search is your gateway into your research. This guide covers two search modes and when to use each.

---

## Quick-Start: Find Something

### Simple Search

```
1. Go to your notebook
2. Type in search box
3. See results (both sources and notes)
4. Click result to view source/note
5. Done!

That works for basic searches.
But you can do much better...
```

---

## Two Search Modes Explained

Open Notebook has two fundamentally different search approaches.

### Search Type 1: TEXT SEARCH (Keyword Matching)

**How it works:**
- You search for words: "transformer"
- System finds chunks containing "transformer"
- Ranked by relevance: frequency, position, context

**Speed:** Very fast (instant)

**When to use:**
- You remember exact words or phrases
- You're looking for specific terms
- You want precise keyword matches
- You need exact quotes

**Example:**
```
Search: "attention mechanism"
Results:
  1. "The attention mechanism allows..." (perfect match)
  2. "Attention and other mechanisms..." (partial match)
  3. "How mechanisms work in attention..." (includes words separately)

All contain "attention" AND "mechanism"
Ranked by how close together they are
```

**What it finds:**
- Exact phrases: "transformer model"
- Individual words: transformer OR model (too broad)
- Names: "Vaswani et al."
- Numbers: "1994", "GPT-4"
- Technical terms: "LSTM", "convolution"

**What it doesn't find:**
- Similar words: searching "attention" won't find "focus"
- Synonyms: searching "large" won't find "big"
- Concepts: searching "similarity" won't find "likeness"

---

### Search Type 2: VECTOR SEARCH (Semantic/Concept Matching)

**How it works:**
- Your search converted to embedding (vector)
- All chunks converted to embeddings
- System finds most similar embeddings
- Ranked by semantic similarity

**Speed:** A bit slower (1-2 seconds)

**When to use:**
- You're exploring a concept
- You don't know exact words
- You want semantically similar content
- You're discovering, not searching

**Example:**
```
Search: "What's the mechanism for understanding in models?"
(Notice: No chunk likely says exactly that)

Results:
  1. "Mechanistic interpretability allows understanding..." (semantic match)
  2. "Feature attribution reveals how models work..." (conceptually similar)
  3. "Attention visualization shows model decisions..." (same topic)

None contain your exact words
But all are semantically related
```

**What it finds:**
- Similar concepts: "understanding" + "interpretation" + "explainability" (all related)
- Paraphrases: "big" and "large" (same meaning)
- Related ideas: "safety" relates to "alignment" (connected concepts)
- Analogies: content about biological learning when searching "learning"

**What it doesn't find:**
- Exact keywords: if you search a rare word, vector search might miss it
- Specific numbers: "1994" vs "1993" are semantically different
- Technical jargon: "LSTM" and "RNN" are different even if related

---

## Decision: Text Search vs. Vector Search?

```
Question: "Do I remember the exact words?"

→ YES: Use TEXT SEARCH
   Example: "I remember the paper said 'attention is all you need'"

→ NO: Use VECTOR SEARCH
   Example: "I'm looking for content about how models process information"

→ UNSURE: Try TEXT SEARCH first (faster)
         If no results, try VECTOR SEARCH

Text search: "I know what I'm looking for"
Vector search: "I'm exploring an idea"
```

---

## Step-by-Step: Using Each Search

### Text Search

```
1. Go to search box
2. Type your keywords: "transformer", "attention", "2017"
3. Press Enter
4. Results appear (usually instant)
5. Click result to see context

Results show:
  - Which source contains it
  - How many times it appears
  - Relevance score
  - Preview of surrounding text
```

### Vector Search

```
1. Go to search box
2. Type your concept: "How do models understand language?"
3. Choose "Vector Search" from dropdown
4. Press Enter
5. Results appear (1-2 seconds)
6. Click result to see context

Results show:
  - Semantically related chunks
  - Similarity score (higher = more related)
  - Preview of surrounding text
  - Different sources mixed together
```

---

## The Ask Feature (Automated Search)

Ask is different from simple search. It automatically searches, synthesizes, and answers.

### How Ask Works

```
Stage 1: QUESTION UNDERSTANDING
  "Compare the approaches in my papers"
  → System: "This asks for comparison"

Stage 2: SEARCH STRATEGY
  → System: "I should search for each approach separately"

Stage 3: PARALLEL SEARCHES
  → Search 1: "Approach in paper A"
  → Search 2: "Approach in paper B"
  (Multiple searches happen at once)

Stage 4: ANALYSIS & SYNTHESIS
  → Per-result analysis: "Based on paper A, the approach is..."
  → Per-result analysis: "Based on paper B, the approach is..."
  → Final synthesis: "Comparing A and B: A differs from B in..."

Result: Comprehensive answer, not just search results
```

### When to Use Ask vs. Simple Search

| Task | Use | Why |
|------|-----|-----|
| "Find the quote about X" | **TEXT SEARCH** | Need exact words |
| "What does source A say about X?" | **TEXT SEARCH** | Direct, fast answer |
| "Find content about X" | **VECTOR SEARCH** | Semantic discovery |
| "Compare A and B" | **ASK** | Comprehensive synthesis |
| "What's the big picture?" | **ASK** | Full analysis needed |
| "How do these sources relate?" | **ASK** | Cross-source synthesis |
| "I remember something about X" | **TEXT SEARCH** | Recall memory |
| "I'm exploring the topic of X" | **VECTOR SEARCH** | Discovery mode |

---

## Advanced Search Strategies

### Strategy 1: Simple Search with Follow-Up

```
1. Text search: "attention mechanism"
   Results: 50 matches

2. Too many. Follow up with vector search:
   "Why is attention useful?" (concept search)
   Results: Most relevant papers/notes

3. Better results with less noise
```

### Strategy 2: Ask for Comprehensive, Then Search for Details

```
1. Ask: "What are the main approaches to X?"
   Result: Comprehensive answer about A, B, C

2. Use that to identify specific sources

3. Text search in those specific sources:
   "Why did they choose method X?"
   Result: Detailed information
```

### Strategy 3: Vector Search for Discovery, Text for Verification

```
1. Vector search: "How do transformers generalize?"
   Results: Related conceptual papers

2. Skim to understand landscape

3. Text search in promising sources:
   "generalization", "extrapolation", "transfer"
   Results: Specific passages to read carefully
```

### Strategy 4: Combine Search with Chat

```
1. Vector search: "What's new in AI 2026?"
   Results: Latest papers

2. Go to Chat
3. Add those papers to context
4. Ask detailed follow-up questions
5. Get deep analysis of results
```

---

## Search Quality Issues & Fixes

### Getting No Results

| Problem | Cause | Solution |
|---------|-------|----------|
| Text search: no results | Word doesn't appear | Try vector search instead |
| Vector search: no results | Concept not in content | Try broader search term |
| Both empty | Content not in notebook | Add sources to notebook |
| | Sources not processed | Wait for processing to complete |

### Getting Too Many Results

| Problem | Cause | Solution |
|---------|-------|----------|
| 1000+ results | Search too broad | Be more specific |
| | All sources | Filter by source |
| | Keyword matches rare words | Use vector search instead |

### Getting Wrong Results

| Problem | Cause | Solution |
|---------|-------|----------|
| Results irrelevant | Search term has multiple meanings | Provide more context |
| | Using text search for concepts | Try vector search |
| Different meaning | Homonym (word means multiple things) | Add context (e.g., "attention mechanism") |

### Getting Low Quality Results

| Problem | Cause | Solution |
|---------|-------|----------|
| Results don't match intent | Vague search term | Be specific ("Who invented X?" vs "X") |
| | Concept not well-represented | Add more sources on that topic |
| | Vector embedding not trained on domain | Use text search as fallback |

---

## Tips for Better Searches

### For Text Search
1. **Be specific** — "attention mechanism" not just "attention"
2. **Use exact phrases** — Put quotes around: "attention is all you need"
3. **Include context** — "LSTM vs attention" not just "attention"
4. **Use technical terms** — These are usually more precise
5. **Try synonyms** — If first search fails, try related terms

### For Vector Search
1. **Ask a question** — "What's the best way to X?" is better than "best way"
2. **Use natural language** — Explain what you're looking for
3. **Be specific about intent** — "Compare X and Y" not "X and Y"
4. **Include context** — "In machine learning, how..." vs just "how..."
5. **Think conceptually** — What idea are you exploring?

### General Tips
1. **Start broad, then narrow** — "AI papers" → "transformers" → "attention mechanism"
2. **Try both search types** — Each finds different things
3. **Use Ask for complex questions** — Don't just search
4. **Save good results as notes** — Create knowledge base
5. **Filter by source if needed** — "Search in Paper A only"

---

## Search Examples

### Example 1: Finding a Specific Fact

**Goal:** "Find the date the transformer was introduced"

```
Step 1: Text search
  "transformer 2017" (or year you remember)

If that works: Done!

If no results: Try
  "attention is all you need" (famous paper title)

Check result for exact date
```

### Example 2: Exploring a Concept

**Goal:** "Find content about alignment interpretability"

```
Step 1: Vector search
  "How do we make AI interpretable?"

Results: Papers on interpretability, transparency, alignment

Step 2: Review results
  See which papers are most relevant

Step 3: Deep dive
  Go to Chat, add top 2-3 papers
  Ask detailed questions about alignment
```

### Example 3: Comprehensive Answer

**Goal:** "How do different approaches to AI safety compare?"

```
Step 1: Ask
  "Compare the main approaches to AI safety in my sources"

Result: Comprehensive analysis comparing approaches

Step 2: Identify sources
  From answer, see which papers were most relevant

Step 3: Deep dive
  Text search in those papers:
  "limitations", "critiques", "open problems"

Step 4: Save as notes
  Create comparison note from Ask result
```

### Example 4: Finding Pattern

**Goal:** "Find all papers mentioning transformers"

```
Step 1: Text search
  "transformer"

Results: All papers mentioning "transformer"

Step 2: Vector search
  "neural network architecture for sequence processing"

Results: Papers that don't say "transformer" but discuss similar concept

Step 3: Combine
  Union of text + vector results shows full landscape

Step 4: Analyze
  Go to Chat with all results
  Ask: "What's common across all these?"
```

---

## Search in the Workflow

How search fits with other features:

```
SOURCES
  ↓
SEARCH (find what matters)
  ├─ Text search (precise)
  ├─ Vector search (exploration)
  └─ Ask (comprehensive)
  ↓
CHAT (explore with follow-ups)
  ↓
TRANSFORMATIONS (batch extract)
  ↓
NOTES (save insights)
```

### Workflow Example

```
1. Add 10 papers to notebook

2. Search: "What's the state of the art?"
   (Vector search explores landscape)

3. Ask: "Compare these 3 approaches"
   (Comprehensive synthesis)

4. Chat: Deep questions about winner
   (Follow-up exploration)

5. Save best insights as notes
   (Knowledge capture)

6. Transform remaining papers
   (Batch extraction for later)

7. Create podcast from notes + sources
   (Share findings)
```

---

## Summary: Know Your Search

**TEXT SEARCH** — "I know what I'm looking for"
- Fast, precise, keyword-based
- Use when you remember exact words/phrases
- Best for: Finding specific facts, quotes, technical terms
- Speed: Instant

**VECTOR SEARCH** — "I'm exploring an idea"
- Slow-ish, concept-based, semantic
- Use when you're discovering connections
- Best for: Concept exploration, related ideas, synonyms
- Speed: 1-2 seconds

**ASK** — "I want a comprehensive answer"
- Auto-searches, auto-analyzes, synthesizes
- Use for complex questions needing multiple sources
- Best for: Comparisons, big-picture questions, synthesis
- Speed: 10-30 seconds

Pick the right tool for your search goal, and you'll find what you need faster.
