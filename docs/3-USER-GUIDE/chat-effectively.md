# Chat Effectively - Conversations with Your Research

Chat is your main tool for exploratory questions and back-and-forth dialogue. This guide covers how to use it effectively.

---

## Quick-Start: Your First Chat

```
1. Go to your notebook
2. Click "Chat"
3. Select which sources to include (context)
4. Type your question
5. Click "Send"
6. Read the response
7. Ask a follow-up (context stays same)
8. Repeat until satisfied
```

That's it! But doing it *well* requires understanding how context works.

---

## Context Management: The Key to Good Chat

Context controls **what the AI is allowed to see**. This is your most important control.

### The Three Levels Explained

**FULL CONTENT**
- AI sees: Complete source text
- Cost: 100 tokens per 1K tokens of source
- Best for: Detailed analysis, precise citations
- Example: "Analyze this research paper closely"

```
You set: Paper A → Full Content
AI sees: Every word of Paper A
AI can: Cite specific sentences, notice nuances
Result: Precise, detailed answers (higher cost)
```

**SUMMARY ONLY**
- AI sees: AI-generated 200-word summary (not full text)
- Cost: ~10-20% of full content cost
- Best for: Background material, reference context
- Example: "Use this for background, focus on the main paper"

```
You set: Paper B → Summary Only
AI sees: Condensed summary, key points
AI can: Reference main ideas but not details
Result: Faster, cheaper answers (loses precision)
```

**NOT IN CONTEXT**
- AI sees: Nothing
- Cost: 0 tokens
- Best for: Confidential, irrelevant, archived content
- Example: "Keep this in notebook but don't use now"

```
You set: Paper C → Not in Context
AI sees: Nothing (completely excluded)
AI can: Never reference it
Result: No cost, no privacy risk for that source
```

### Setting Context (Step by Step)

```
1. Click "Select Sources"
   (Shows list of all sources in notebook)

2. For each source:
   □ Checkbox: Include or exclude

   Level dropdown:
   ├─ Full Content
   ├─ Summary Only
   └─ Excluded

3. Check your selections
   Example:
   ✓ Paper A (Full Content) - "Main focus"
   ✓ Paper B (Summary Only) - "Background"
   ✓ Paper C (Excluded) - "Keep private"
   □ Paper D (Not included) - "Not relevant"

4. Click "Save Context"

5. Now chat uses these settings
```

### Context Strategies

**Strategy 1: Minimalist**
- Main source: Full Content
- Everything else: Excluded
- Result: Focused, cheap, precise

```
Use when:
  - Analyzing one source deeply
  - Budget-conscious
  - Want focused answers
```

**Strategy 2: Comprehensive**
- All sources: Full Content
- Result: All context considered, expensive

```
Use when:
  - Comprehensive analysis
  - Unlimited budget
  - Want AI to see everything
```

**Strategy 3: Tiered**
- Primary sources: Full Content
- Secondary sources: Summary Only
- Background/reference: Excluded
- Result: Balanced cost/quality

```
Use when:
  - Mix of important and reference material
  - Want thorough but not expensive
  - Most common strategy
```

**Strategy 4: Privacy-First**
- Sensitive docs: Excluded
- Public research: Full Content
- Result: Never send confidential data

```
Use when:
  - Company confidential materials
  - Personal sensitive data
  - Complying with data protection
```

---

## Asking Effective Questions

### Good Questions vs. Poor Questions

**Poor Question**
```
"What do you think?"

Problems:
- Too vague (about what?)
- No context (what am I analyzing?)
- Can't verify answer (citing what?)

Result: Generic, shallow answer
```

**Good Question**
```
"Based on the paper's methodology section,
what are the three main limitations the authors acknowledge?
Please cite which pages mention each one."

Strengths:
- Specific about what you want
- Clear scope (methodology section)
- Asks for citations
- Requires deep reading

Result: Precise, verifiable, useful answer
```

### Question Patterns That Work

**Factual Questions**
```
"What does the paper say about X?"
"Who are the authors?"
"What year was this published?"

Result: Simple, factual answers with citations
```

**Analysis Questions**
```
"How does this approach differ from the traditional method?"
"What are the main assumptions underlying this argument?"
"Why do you think the author chose this methodology?"

Result: Deeper thinking, comparison, critique
```

**Synthesis Questions**
```
"How do these two sources approach the problem differently?"
"What's the common theme across all three papers?"
"If we combine these approaches, what would we get?"

Result: Cross-source insights, connections
```

**Actionable Questions**
```
"What are the practical implications of this research?"
"How could we apply these findings to our situation?"
"What's the next logical research direction?"

Result: Practical, forward-looking answers
```

### The SPECIFIC Formula

Good questions have:

1. **SCOPE** - What are you analyzing?
   "In this research paper..."
   "Looking at these three articles..."
   "Based on your experience..."

2. **SPECIFICITY** - Exactly what do you want?
   "...the methodology..."
   "...main findings..."
   "...recommended next steps..."

3. **CONSTRAINT** - Any limits?
   "...in 3 bullet points..."
   "...with citations to page numbers..."
   "...comparing these two approaches..."

4. **VERIFICATION** - How can you check it?
   "...with specific quotes..."
   "...cite your sources..."
   "...link to the relevant section..."

**Example:**
```
Poor: "What about transformers?"
Good: "In this research paper on machine learning,
      explain the transformer architecture in 2-3 sentences,
      then cite which page describes the attention mechanism."
```

---

## Follow-Up Questions (The Real Power of Chat)

Chat's strength is dialogue. You ask, get an answer, ask more.

### Building on Responses

```
First question:
"What's the main finding?"

AI: "The study shows X [citation]"

Follow-up question:
"How does that compare to Y research?"

AI: "The key difference is Z [citation]"

Next question:
"Why do you think that difference matters?"

AI: "Because it affects A, B, C [explained]"
```

### Iterating Toward Understanding

```
Round 1: Get overview
"What's this source about?"

Round 2: Get details
"What's the most important part?"

Round 3: Compare
"How does it relate to my notes on X?"

Round 4: Apply
"What should I do with this information?"
```

### Changing Direction

```
Context stays same, but you ask new questions:

Question 1: "What's the methodology?"
Question 2: "What are the limitations?"
Question 3: "What about the ethical implications?"
Question 4: "Who else has done similar work?"

All in one conversation, reusing context.
```

### Adjusting Context Between Rounds

```
After question 3, you realize:
"I need more context from another source"

1. Click "Adjust Context"
2. Add new source or change context level
3. Your conversation history stays
4. Continue asking with new context
```

---

## Citations and Verification

Citations are how you verify that the AI's answer is accurate.

### Understanding Citations

```
AI Response with Citation:
"The paper reports a 95% accuracy rate [see page 12]"

What this means:
✓ The claim "95% accuracy rate" is from page 12
✓ You can verify by reading page 12
✓ If page 12 doesn't say that, the AI hallucinated
```

### Requesting Better Citations

```
If you get a response without citations:

Ask: "Please cite the page number for that claim"
or: "Show me where you found that information"

AI will:
- Find the citation
- Provide page numbers
- Show you the source
```

### Verification Workflow

```
1. Get answer from Chat
2. Check citation (which source? which page?)
3. Click citation link (if available)
4. See the actual text in source
5. Does it really say what AI claimed?

If YES: Great, you can use this answer
If NO: The AI hallucinated, ask for correction
```

---

## Common Chat Patterns

### Pattern 1: Deep Dive into One Source

```
1. Set context: One source (Full Content)
2. Question 1: Overview
3. Question 2: Main argument
4. Question 3: Evidence for argument
5. Question 4: Limitations
6. Question 5: Next steps

Result: Complete understanding of one source
```

### Pattern 2: Comparative Analysis

```
1. Set context: 2-3 sources (all Full Content)
2. Question 1: What does each source say about X?
3. Question 2: How do they agree?
4. Question 3: How do they disagree?
5. Question 4: Which approach is stronger?

Result: Understanding differences and trade-offs
```

### Pattern 3: Research Exploration

```
1. Set context: Many sources (mix of Full/Summary)
2. Question 1: What are the main perspectives?
3. Question 2: What's missing from these views?
4. Question 3: What questions does this raise?
5. Question 4: What should I research next?

Result: Understanding landscape and gaps
```

### Pattern 4: Problem Solving

```
1. Set context: Relevant sources (Full Content)
2. Question 1: What's the problem?
3. Question 2: What approaches exist?
4. Question 3: Pros and cons of each?
5. Question 4: Which would work best for [my situation]?

Result: Decision-making informed by research
```

---

## Optimizing for Cost

Chat uses tokens for every response. Here's how to use efficiently:

### Reduce Token Usage

**Minimize context**
```
Option A: All sources, Full Content
  Cost per response: 5,000 tokens

Option B: Only relevant sources, Summary Only
  Cost per response: 1,000 tokens

Savings: 80% cheaper, same conversation
```

**Shorter questions**
```
Verbose: "Could you please analyze the methodology
         section of this paper and explain in detail
         what the authors did?"

Concise: "Summarize the methodology in 2-3 points."

Savings: 20-30% per response
```

**Use cheaper models**
```
GPT-4o: $0.15 per 1M input tokens
GPT-4o-mini: $0.03 per 1M input tokens
Claude Sonnet: $0.90 per 1M input tokens

For chat: Mini/Haiku models are usually fine
For deep analysis: Sonnet/Opus worth the cost
```

### Budget Strategies

**Exploration budget**
- Use cheap model
- Broad context (understand landscape)
- Short questions
- Result: Low cost, good overview

**Analysis budget**
- Use powerful model
- Focused context (main source only)
- Detailed questions
- Result: Higher cost, deep insights

**Synthesis budget**
- Use powerful model for final synthesis
- Multiple sources (Full Content)
- Complex comparative questions
- Result: Expensive but valuable output

---

## Troubleshooting Chat Issues

### Poor Responses

| Problem | Cause | Solution |
|---------|-------|----------|
| Generic answers | Vague question | Be specific (see question patterns) |
| Missing context | Not enough in context | Add sources or change to Full Content |
| Incorrect info | Source not in context | Add the relevant source |
| Hallucinating | Model confused | Ask for citations, verify claims |
| Shallow analysis | Wrong model | Switch to more powerful model |

### High Costs

| Problem | Cause | Solution |
|---------|-------|----------|
| Expensive per response | Too much context | Use Summary Only or exclude sources |
| Many follow-ups | Exploratory chat | Use Ask instead for single comprehensive answer |
| Long conversations | Keeping history | Archive old chats, start fresh |
| Large sources | Full text in context | Use Summary Only for large documents |

---

## Best Practices

### Before You Chat

- [ ] Add sources you'll need
- [ ] Decide context strategy (Tiered is usually best)
- [ ] Choose model (cheaper for exploration, powerful for analysis)
- [ ] Have a question in mind

### During Chat

- [ ] Ask specific questions (use SPECIFIC formula)
- [ ] Check citations for factual claims
- [ ] Follow up on unclear points
- [ ] Adjust context if you need different sources

### After Chat

- [ ] Save good responses as notes
- [ ] Archive conversation if you're done
- [ ] Organize notes for future reference
- [ ] Use insights in other features (Ask, Transformations, Podcasts)

---

## When to Use Chat vs. Ask

**Use CHAT when:**
- You want a dialogue
- You're exploring a topic
- You'll ask multiple related questions
- You want to adjust context during conversation
- You're not sure exactly what you need

**Use ASK when:**
- You have one specific question
- You want a comprehensive answer
- You want the system to auto-search
- You want one response, not dialogue
- You want maximum tokens spent on search

---

## Summary: Chat as Conversation

Chat is fundamentally different from asking ChatGPT directly:

| Aspect | ChatGPT | Open Notebook Chat |
|--------|---------|-------------------|
| **Source control** | None (uses training) | You control which sources are visible |
| **Cost control** | Per token | Per token, but context is your choice |
| **Iteration** | Works | Works, with your sources changing dynamically |
| **Citations** | Made up often | Tied to your sources (verifiable) |
| **Privacy** | Your data to OpenAI | Your data stays local (unless you choose) |

The key insight: **Chat is retrieval-augmented generation.** AI sees only what you put in context. You control the conversation and the information flow.

That's why Chat is powerful for research. You're not just talking to an AI; you're having a conversation with your research itself.
