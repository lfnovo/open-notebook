# Citations - Verify and Trust AI Responses

Citations connect AI responses to your source materials. This guide covers how to use and verify them.

---

## Why Citations Matter

Every AI-generated response in Open Notebook includes citations to your sources. This lets you:

- **Verify claims** - Check that AI actually read what it claims
- **Find original context** - See the full passage around a quote
- **Catch hallucinations** - Spot when AI makes things up
- **Build credibility** - Your notes have traceable sources

---

## Quick Start: Using Citations

### Reading Citations

```
AI Response:
"The study found a 95% accuracy rate [1] using the proposed method."

[1] = Click to see source

What happens when you click:
→ Opens the source document
→ Highlights the relevant section
→ You can verify the claim
```

### Requesting Better Citations

If a response lacks citations, ask:

```
"Please cite the specific page or section for that claim."
"Where in the document does it say that?"
"Can you quote the exact text?"
```

---

## How Citations Work

### Automatic Generation

When AI references your sources, citations are generated automatically:

```
1. AI analyzes your question
2. Retrieves relevant source chunks
3. Generates response with inline citations
4. Links citations to original source locations
```

### Citation Format

```
Inline format:
"The researchers concluded X [1] and Y [2]."

Reference list:
[1] Paper Title - Section 3.2
[2] Report Name - Page 15

Clickable: Each [number] links to the source
```

---

## Verifying Citations

### The Verification Workflow

```
Step 1: Read AI response
        "The model achieved 95% accuracy [1]"

Step 2: Click citation [1]
        → Opens source document
        → Shows relevant passage

Step 3: Verify the claim
        Does source actually say 95%?
        Is context correct?
        Any nuance missed?

Step 4: Trust or correct
        ✓ Accurate → Use the insight
        ✗ Wrong → Ask AI to correct
```

### What to Check

| Check | Why |
|-------|-----|
| **Exact numbers** | AI sometimes rounds or misremembers |
| **Context** | Quote might mean something different in context |
| **Attribution** | Is this the source's claim or someone they cited? |
| **Completeness** | Did AI miss important caveats? |

---

## Citations in Different Features

### Chat Citations

```
Context: Sources you selected
Citations: Reference chunks used in response
Verification: Click to see original text
Save: Citations preserved when saving as note
```

### Ask Feature Citations

```
Context: Auto-searched across all sources
Citations: Multiple sources synthesized
Verification: Each source linked separately
Quality: Often more comprehensive than Chat
```

### Transformation Citations

```
Context: Single source being transformed
Citations: Points back to original document
Verification: Compare output to source
Use: When you need structured extraction
```

---

## Saving Citations

### In Notes

When you save an AI response as a note, citations are preserved:

```
Original response:
"According to the paper [1], the method works by..."

Saved note includes:
- The text
- The citation link
- Reference to source document
```

### Exporting

Citations work in exports:

| Format | Citation Behavior |
|--------|-------------------|
| **Markdown** | Links preserved as `[text](link)` |
| **Copy/Paste** | Plain text with reference numbers |
| **PDF** | Clickable references (if supported) |

---

## Citation Quality Tips

### Get Better Citations

**Be specific in questions:**
```
Poor: "What does it say about X?"
Good: "What does page 15 say about X? Please quote directly."
```

**Request citation format:**
```
"Include page numbers for each claim."
"Cite specific sections, not just document names."
```

**Use Full Content context:**
```
Summary Only → Less precise citations
Full Content → Exact quotes possible
```

### When Citations Are Missing

| Situation | Cause | Solution |
|-----------|-------|----------|
| No citations | AI used general knowledge | Ask: "Base your answer only on my sources" |
| Vague citations | Source not in Full Content | Change context level |
| Wrong citations | AI confused sources | Ask to verify with quotes |

---

## Common Issues

### "Citation doesn't match claim"

```
Problem: AI says X, but source says Y

What happened:
- AI paraphrased incorrectly
- AI combined multiple sources confusingly
- Source was taken out of context

Solution:
1. Click citation to see original
2. Note the discrepancy
3. Ask AI: "The source says Y, not X. Please correct."
```

### "Can't find cited section"

```
Problem: Citation link doesn't show relevant text

What happened:
- Source was chunked differently than expected
- Information spread across multiple sections
- Processing missed some content

Solution:
1. Search within source for key terms
2. Ask AI for more specific location
3. Re-process source if needed
```

### "No citations at all"

```
Problem: AI response has no source references

What happened:
- Sources not in context
- Question asked for opinion/general knowledge
- Model didn't find relevant content

Solution:
1. Check context settings
2. Rephrase: "Based on my sources, what..."
3. Add more relevant sources
```

---

## Best Practices

### For Research Integrity

1. **Always verify important claims** - Don't trust AI blindly
2. **Check context** - Quotes can be misleading out of context
3. **Note limitations** - AI might miss nuance
4. **Keep source access** - Don't delete sources you cite

### For Academic Work

1. **Use Full Content** for documents you'll cite
2. **Request specific page numbers**
3. **Cross-check with original sources**
4. **Document your verification process**

### For Professional Use

1. **Verify before sharing** - Check claims clients will see
2. **Keep citation trail** - Save notes with sources linked
3. **Be transparent** - Note when insights are AI-assisted

---

## Summary

```
Citations = Your verification system

How to use:
1. Read AI response
2. Note citation markers [1], [2], etc.
3. Click to see original source
4. Verify claim matches source
5. Trust verified insights

When citations fail:
- Ask for specific quotes
- Change to Full Content
- Request page numbers
- Verify manually

Why it matters:
- AI can hallucinate
- Context can change meaning
- Trust requires verification
- Good research needs sources
```

Citations aren't just references — they're your quality control. Use them to build research you can trust.
