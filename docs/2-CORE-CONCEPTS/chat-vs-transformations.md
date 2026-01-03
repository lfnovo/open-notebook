# Chat vs. Ask vs. Transformations - Which Tool for Which Job?

Open Notebook offers different ways to work with your research. Understanding when to use each is key to using the system effectively.

---

## The Three Interaction Modes

### 1. CHAT - Conversational Exploration with Manual Context

**What it is:** Have a conversation with AI about selected sources.

**The flow:**
```
1. You select which sources to include ("in context")
2. You ask a question
3. AI responds using ONLY those sources
4. You ask follow-up questions (context stays same)
5. You change sources or context level, then continue
```

**Context management:** You explicitly choose which sources the AI can see.

**Conversational:** Multiple questions with shared history.

**Example:**
```
You: [Select sources: "paper1.pdf", "research_notes.txt"]
     [Set context: Full content for paper1, Summary for notes]

You: "What's the main argument in these sources?"
AI:  "Paper 1 argues X [citation]. Your notes emphasize Y [citation]."

You: "How do they differ?"
AI:  "Paper 1 focuses on X [citation], while your notes highlight Y [citation]..."

You: [Now select different sources]

You: "Compare to this other perspective"
AI:  "This new source takes a different approach..."
```

**Best for:**
- Exploring a focused topic with specific sources
- Having a dialogue (multiple back-and-forth questions)
- When you know which sources matter
- When you want tight control over what goes to AI

---

### 2. ASK - Automated Comprehensive Search

**What it is:** Ask one complex question, system automatically finds relevant content.

**The flow:**
```
1. You ask a comprehensive question
2. System analyzes the question
3. System automatically searches your sources
4. System retrieves relevant chunks
5. System synthesizes answer from all results
6. You get one detailed answer (not conversational)
```

**Context management:** Automatic. System figures out what's relevant.

**Non-conversational:** One question → one answer. No follow-ups.

**Example:**
```
You: "How do these papers compare their approaches to alignment?
      What does each one recommend?"

System:
  - Breaks down the question into search strategies
  - Searches all sources for alignment approaches
  - Searches all sources for recommendations
  - Retrieves top 10 relevant chunks
  - Synthesizes: "Paper A recommends X [citation].
                  Paper B recommends Y [citation].
                  They differ in Z."

You: [Get back one comprehensive answer]
     [If you want to follow up, use Chat instead]
```

**Best for:**
- Comprehensive, one-time questions
- Comparing multiple sources at once
- When you want the system to decide what's relevant
- Complex questions that need multiple search angles
- When you don't need a back-and-forth conversation

---

### 3. TRANSFORMATIONS - Batch Processing with Templates

**What it is:** Apply a reusable template to one or more sources and get structured outputs.

**The flow:**
```
1. You define a transformation (or choose a preset)
   "Extract: main argument, methodology, limitations"

2. You apply it to one or more sources
   OR system applies it to all sources

3. For each source:
   - Source content + transformation prompt → AI
   - Result stored as new insight/note

4. You get back
   - Structured outputs (main argument, methodology, limitations)
   - Saved as notes in your notebook
```

**Context management:** You choose which sources to transform.

**Batch processing:** Process multiple sources at once.

**Example:**
```
You: Define transformation
     "For each academic paper, extract:
      - Main research question
      - Methodology used
      - Key findings
      - Limitations and gaps
      - Recommended next research"

You: Apply to 10 papers

System:
  - For each paper, runs the transformation
  - Results stored as 10 new notes
  - Each note has the structure you defined

You: Now you have structured notes from all 10 papers
     Perfect for writing a literature review or comparison
```

**Best for:**
- Extracting the same information from multiple sources
- Creating structured summaries
- Building a knowledge base of categorized insights
- When you want consistent, reusable templates
- Batch processing multiple sources

---

## Decision Tree: Which Tool to Use?

```
What are you trying to do?

│
├─→ "I want to have a conversation about this topic"
│   └─→ Is the conversation exploratory or fixed?
│       ├─→ Exploratory (I'll ask follow-ups)
│       │   └─→ USE: CHAT
│       │
│       └─→ Fixed (One question → done)
│           └─→ Go to next question
│
├─→ "I need to compare these sources or get a comprehensive answer"
│   └─→ USE: ASK
│
├─→ "I want to extract the same info from many sources"
│   └─→ USE: TRANSFORMATIONS
│
└─→ "I just want to read and search"
    └─→ USE: Search (text or vector)
        OR read your notes
```

---

## Side-by-Side Comparison

| Aspect | CHAT | ASK | TRANSFORMATIONS |
|--------|------|-----|-----------------|
| **What's it for?** | Conversational exploration | Comprehensive Q&A | Batch extraction |
| **# of questions** | Multiple (conversational) | One | One template, many sources |
| **Context control** | Manual (you choose) | Automatic (system searches) | Manual (you choose) |
| **Conversational?** | Yes (follow-ups work) | No (one question only) | No (batch process) |
| **Output** | Natural conversation | Natural answer | Structured notes |
| **Time** | Quick (back-and-forth) | Longer (comprehensive) | Batch (all at once) |
| **Best when** | Exploring & uncertain | Need full picture | Want consistency |
| **Model speed** | Any | Fast preferred | Any |

---

## Workflow Examples

### Example 1: Academic Research

```
Goal: Write literature review from 15 papers

Step 1: TRANSFORMATIONS
  - Define: "Extract abstract, methodology, findings, relevance"
  - Apply to all 15 papers
  - Get back 15 structured notes

Step 2: Read the notes
  - Now you have consistent summaries

Step 3: CHAT or ASK
  - Chat: "Help me organize these by theme"
  - Ask: "What are the common methodologies across these papers?"

Step 4: Write your review
  - Use the transformations as foundation
  - Use chat/ask insights for structure
```

### Example 2: Product Research

```
Goal: Understand customer feedback from interviews

Step 1: Add sources (interview transcripts)

Step 2: ASK
  - "What are the top 10 pain points mentioned?"
  - Get comprehensive answer with citations

Step 3: CHAT
  - "Can you help me group these by severity?"
  - Continue conversation to prioritize

Step 4: TRANSFORMATIONS (optional)
  - Define: "Extract: pain point, frequency, who mentioned it"
  - Apply to all interviews
  - Get structured data for analysis
```

### Example 3: Policy Analysis

```
Goal: Compare policy documents

Step 1: Add all policy documents as sources

Step 2: ASK
  - "How do these policies differ on climate measures?"
  - System searches all docs, gives comprehensive comparison

Step 3: CHAT (if needed)
  - "Which policy is most aligned with X goals?"
  - Have discussion about trade-offs

Step 4: Export notes
  - Save AI responses as notes for reports
```

---

## Context Management: The Control Panel

All three modes let you control what the AI sees.

### In CHAT and TRANSFORMATIONS
```
You choose:
  - Which sources to include
  - Context level for each:
    ✓ Full Content (send complete text)
    ✓ Summary Only (send AI summary, not full text)
    ✓ Not in Context (exclude entirely)

Example:
  Paper A: Full Content (analyzing closely)
  Paper B: Summary Only (background)
  Paper C: Not in Context (confidential)
```

### In ASK
```
Context is automatic:
  - System searches ALL your sources
  - Retrieves most relevant chunks
  - Sends those to AI

But you can:
  - Search in specific notebook
  - Filter by source type
  - Use the results to decide context for follow-up Chat
```

---

## Model Selection

Each mode works with different models:

### CHAT
- **Any model** works fine
- Fast models (GPT-4o mini, Claude Haiku): Quick responses, good for conversation
- Powerful models (GPT-4o, Claude Sonnet): Better reasoning, better for complex topics

### ASK
- **Fast models preferred** (because it processes multiple searches)
- Can use powerful models if you want deep synthesis
- Example: GPT-4 for strategy planning, GPT-4o-mini for quick facts

### TRANSFORMATIONS
- **Any model** works
- Fast models (cost-effective for batch processing)
- Powerful models (better quality extractions)

---

## Advanced: Chaining Modes Together

You can combine these modes:

```
TRANSFORMATIONS → CHAT
  1. Use transformations to extract structured data
  2. Use chat to discuss the results

ASK → TRANSFORMATIONS
  1. Use Ask to understand what matters
  2. Use Transformations to extract it from remaining sources

CHAT → Save as Note → TRANSFORMATIONS
  1. Have conversation (Chat)
  2. Save good responses as notes
  3. Use those notes as context for transformations
```

---

## Summary: When to Use Each

| Situation | Use | Why |
|-----------|-----|-----|
| "I want to explore a topic with follow-up questions" | **CHAT** | Conversational, you control context |
| "I need a comprehensive answer to one complex question" | **ASK** | Automatic search, synthesized answer |
| "I want consistent summaries from 10+ sources" | **TRANSFORMATIONS** | Template reuse, batch processing |
| "I'm comparing two specific sources" | **CHAT** | Select just those 2, have discussion |
| "I need to categorize all sources by X criteria" | **TRANSFORMATIONS** | Extract category for each source |
| "I want to understand the big picture across all sources" | **ASK** | Automatic comprehensive search |
| "I want to build a knowledge base" | **TRANSFORMATIONS** | Create structured notes |
| "I want to iterate on understanding" | **CHAT** | Multiple questions, refine thinking |

The key insight: **Different questions need different tools.** Open Notebook gives you all three because research rarely fits one mode.
