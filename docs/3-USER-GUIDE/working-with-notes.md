# Working with Notes - Capturing and Organizing Insights

Notes are your processed knowledge. This guide covers how to create, organize, and use them effectively.

---

## What Are Notes?

Notes are your **research output** — the insights you capture from analyzing sources. They can be:

- **Manual** — You write them yourself
- **AI-Generated** — From Chat responses, Ask results, or Transformations
- **Hybrid** — AI insight + your edits and additions

Unlike sources (which never change), notes are mutable — you edit, refine, and organize them.

---

## Quick-Start: Create Your First Note

### Method 1: Manual Note (Write Yourself)

```
1. In your notebook, go to "Notes" section
2. Click "Create New Note"
3. Give it a title: "Key insights from source X"
4. Write your content (markdown supported)
5. Click "Save"
6. Done! Note appears in your notebook
```

### Method 2: Save from Chat

```
1. Have a Chat conversation
2. Get a good response from AI
3. Click "Save as Note" button under response
4. Give the note a title
5. Add any additional context
6. Click "Save"
7. Done! Note appears in your notebook
```

### Method 3: Apply Transformation

```
1. Go to "Transformations"
2. Select a template (or create custom)
3. Click "Apply to sources"
4. Select which sources to transform
5. Wait for processing
6. New notes automatically appear
7. Done! Each source produces one note
```

---

## Creating Manual Notes

### Basic Structure

```
Title: "What you're capturing"
       (Make it descriptive)

Content:
  - Main points
  - Your analysis
  - Questions raised
  - Next steps

Metadata:
  - Tags: How to categorize
  - Related sources: Which documents influenced this
  - Date: Auto-added when created
```

### Markdown Support

You can format notes with markdown:

```markdown
# Heading
## Subheading
### Sub-subheading

**Bold text** for emphasis
*Italic text* for secondary emphasis

- Bullet lists
- Like this

1. Numbered lists
2. Like this

> Quotes and important callouts

[Links work](https://example.com)
```

### Example Note Structure

```markdown
# Key Findings from "AI Safety Paper 2025"

## Main Argument
The paper argues that X approach is better than Y because...

## Methodology
The authors use [methodology] to test this hypothesis.

## Key Results
- Result 1: [specific finding with citation]
- Result 2: [specific finding with citation]
- Result 3: [specific finding with citation]

## Gaps & Limitations
1. The paper assumes X, which might not hold in Y scenario
2. Limited to Z population/domain
3. Future work needed on A, B, C

## My Thoughts
- This connects to previous research on...
- Potential application in...

## Next Steps
- [ ] Read the referenced paper on X
- [ ] Find similar studies on Y
- [ ] Discuss implications with team
```

---

## AI-Generated Notes: Three Sources

### 1. Save from Chat

```
Workflow:
  Chat → Good response → "Save as Note"
         → Edit if needed → Save

When to use:
  - AI response answers your question well
  - You want to keep the answer for reference
  - You're building a knowledge base from conversations

Quality:
  - Quality = quality of your Chat question
  - Better context = better responses = better notes
  - Ask specific questions for useful notes
```

### 2. Save from Ask

```
Workflow:
  Ask → Comprehensive answer → "Save as Note"
      → Edit if needed → Save

When to use:
  - You need a one-time comprehensive answer
  - You want to save the synthesized result
  - Building a knowledge base of comprehensive answers

Quality:
  - System automatically found relevant sources
  - Results already have citations
  - Often higher quality than Chat (more thorough)
```

### 3. Transformations (Batch Processing)

```
Workflow:
  Define transformation → Apply to sources → Notes auto-created
                      → Review & edit → Organize

Example Transformation:
  Template: "Extract: main argument, methodology, key findings"
  Apply to: 5 sources
  Result: 5 new notes with consistent structure

When to use:
  - Same extraction from many sources
  - Building structured knowledge base
  - Creating consistent summaries
```

---

## Using Transformations for Batch Insights

### Built-in Transformations

Open Notebook comes with presets:

**Summary**
```
Extracts: Main points, key arguments, conclusions
Output: 200-300 word summary of source
Best for: Quick reference summaries
```

**Key Concepts**
```
Extracts: Main ideas, concepts, terminology
Output: List of concepts with explanations
Best for: Learning and terminology
```

**Methodology**
```
Extracts: Research approach, methods, data
Output: How the research was conducted
Best for: Academic sources, methodology review
```

**Takeaways**
```
Extracts: Actionable insights, recommendations
Output: What you should do with this information
Best for: Practical/business sources
```

### How to Apply Transformation

```
1. Go to "Transformations"
2. Select a template
3. Click "Apply"
4. Select which sources (one or many)
5. Wait for processing (usually 30 seconds - 2 minutes)
6. New notes appear in your notebook
7. Edit if needed
```

### Create Custom Transformation

```
1. Click "Create Custom Transformation"
2. Write your extraction template:

   Example:
   "For this academic paper, extract:
    - Central research question
    - Hypothesis tested
    - Methodology used
    - Key findings (numbered)
    - Limitations acknowledged
    - Recommendations for future work"

3. Click "Save Template"
4. Apply to one or many sources
5. System generates notes with consistent structure
```

---

## Organizing Notes

### Naming Conventions

**Option 1: Date-based**
```
2026-01-03 - Key points from X source
2026-01-04 - Comparison between A and B
Benefit: Easy to see what you did when
```

**Option 2: Topic-based**
```
AI Safety - Alignment approaches
AI Safety - Interpretability research
Benefit: Groups by subject matter
```

**Option 3: Type-based**
```
SUMMARY: Paper on X
QUESTION: What about Y?
INSIGHT: Connection between Z and W
Benefit: Easy to filter by type
```

**Option 4: Source-based**
```
From: Paper A - Main insights
From: Video B - Interesting implications
Benefit: Easy to trace back to sources
```

**Best practice:** Combine approaches
```
[Date] [Source] - [Topic] - [Type]
2026-01-03 - Paper A - AI Safety - Takeaways
```

### Using Tags

Tags are labels for categorization. Add them when creating notes:

```
Example tags:
  - "primary-research" (direct source analysis)
  - "background" (supporting material)
  - "methodology" (about research methods)
  - "insights" (your original thinking)
  - "questions" (open questions raised)
  - "follow-up" (needs more work)
  - "published" (ready to share/use)
```

**Benefits of tags:**
- Filter notes by tag
- Find all notes of a type
- Organize workflow (e.g., find all "follow-up" notes)

### Note Linking & References

You can reference sources within notes:

```markdown
# Analysis of Paper A

As shown in Paper A (see "main argument" section),
the authors argue that...

## Related Sources
- Paper B discusses similar approach
- Video C shows practical application
- My note on "Comparative analysis" has more
```

---

## Editing and Refining Notes

### Improving AI-Generated Notes

```
AI Note:
  "The paper discusses machine learning"

What you might change:
  "The paper proposes a supervised learning approach
   to classification problems, using neural networks
   with attention mechanisms (see pp. 15-18)."

How to edit:
  1. Click note
  2. Click "Edit"
  3. Refine the content
  4. Click "Save"
```

### Adding Citations

```
When saving from Chat/Ask:
  - Citations auto-added
  - Shows which sources informed answer
  - You can verify by clicking

When manual notes:
  - Add manually: "From Paper A, page 15: ..."
  - Or reference: "As discussed in [source]"
```

---

## Searching Your Notes

Notes are fully searchable:

### Text Search
```
Find exact phrase: "attention mechanism"
Results: All notes containing that phrase
Use when: Looking for specific terms or quotes
```

### Vector/Semantic Search
```
Find concept: "How do models understand?"
Results: Notes about interpretability, mechanistic understanding, etc.
Use when: Exploring conceptually (words not exact)
```

### Combined Search
```
Text search notes → Find keyword matches
Vector search notes → Find conceptual matches
Both work across sources + notes together
```

---

## Exporting and Sharing Notes

### Options

**Copy to clipboard**
```
Click "Share" → "Copy" → Paste anywhere
Good for: Sharing one note via email/chat
```

**Export as Markdown**
```
Click "Share" → "Export as MD" → Saves as .md file
Good for: Sharing with others, version control
```

**Create note collection**
```
Select multiple notes → "Export collection"
→ Creates organized markdown document
Good for: Sharing a topic overview
```

**Publish to web**
```
Click "Publish" → Get shareable link
Good for: Publishing publicly (if desired)
```

---

## Organizing Your Notebook's Notes

### By Research Phase

**Phase 1: Discovery**
- Initial summaries
- Questions raised
- Interesting findings

**Phase 2: Deep Dive**
- Detailed analysis
- Comparative insights
- Methodology reviews

**Phase 3: Synthesis**
- Connections across sources
- Original thinking
- Conclusions

### By Content Type

**Summaries**
- High-level overviews
- Generated by transformations
- Quick reference

**Questions**
- Open questions
- Things to research more
- Gaps to fill

**Insights**
- Your original analysis
- Connections made
- Conclusions reached

**Tasks**
- Follow-up research
- Sources to add
- People to contact

---

## Using Notes in Other Features

### In Chat

```
You can reference notes:
"Based on my note 'Key findings from A',
how does this compare to B?"

Notes become part of context.
Treated like sources but smaller/more focused.
```

### In Transformations

```
Notes can be transformed:
1. Select notes as input
2. Apply transformation
3. Get new derived notes

Example: Transform 5 analysis notes → Create synthesis
```

### In Podcasts

```
Notes are used to create podcast content:
1. Generate podcast for notebook
2. System includes notes in content selection
3. Notes become part of episode outline
```

---

## Best Practices

### For Manual Notes
1. **Write clearly** — Future you will appreciate it
2. **Add context** — Why this matters, not just what it says
3. **Link to sources** — You can verify later
4. **Date them** — Track your thinking over time
5. **Tag immediately** — Don't defer organization

### For AI-Generated Notes
1. **Review before saving** — Verify quality
2. **Edit for clarity** — AI might miss nuance
3. **Add your thoughts** — Make it your own
4. **Include citations** — Understand sources
5. **Organize right away** — While context is fresh

### For Organization
1. **Consistent naming** — Your future self will thank you
2. **Tag everything** — Makes filtering later much easier
3. **Link related notes** — Create knowledge network
4. **Review periodically** — Refactor as understanding evolves
5. **Archive old notes** — Keep working space clean

---

## Common Mistakes

| Mistake | Problem | Solution |
|---------|---------|----------|
| Save every Chat response | Notebook becomes cluttered with low-quality notes | Only save good responses that answer your questions |
| Don't add tags | Can't find notes later | Tag immediately when creating |
| Poor note titles | Can't remember what's in them | Use descriptive titles, include key concept |
| Never link notes together | Miss connections between ideas | Add references to related notes |
| Forget the source | Can't verify claims later | Always link back to source |
| Never edit AI notes | Keep generic AI responses | Refine for clarity and context |
| Create one giant note | Too long to be useful | Split into focused notes by subtopic |

---

## Summary: Note Lifecycle

```
1. CREATE
   ├─ Manual: Write from scratch
   ├─ From Chat: Save good response
   ├─ From Ask: Save synthesis
   └─ From Transform: Batch process

2. EDIT & REFINE
   ├─ Improve clarity
   ├─ Add context
   ├─ Fix AI mistakes
   └─ Add citations

3. ORGANIZE
   ├─ Name clearly
   ├─ Add tags
   ├─ Link related
   └─ Categorize

4. USE
   ├─ Reference in Chat
   ├─ Transform for synthesis
   ├─ Export for sharing
   └─ Build on with new questions

5. MAINTAIN
   ├─ Periodically review
   ├─ Update as understanding grows
   ├─ Archive when done
   └─ Learn from organized knowledge
```

Your notes become your actual knowledge base. The more you invest in organizing them, the more valuable they become.
