# User Guide - How to Use Open Notebook

This guide covers practical, step-by-step usage of Open Notebook features. You already understand the concepts; now learn how to actually use them.

> **Prerequisite**: Review [2-CORE-CONCEPTS](../2-CORE-CONCEPTS/index.md) first to understand the mental models (notebooks, sources, notes, chat, transformations, podcasts).

---

## Start Here

### [Interface Overview](interface-overview.md)
Learn the layout before diving in. Understand the three-panel design and where everything is.

---

## Eight Core Features

### 1. [Adding Sources](adding-sources.md)
How to bring content into your notebook. Supports PDFs, web links, audio, video, text, and more.

**Quick links:**
- Upload a PDF or document
- Add a web link or article
- Transcribe audio or video
- Paste text directly
- Common mistakes + fixes

---

### 2. [Working with Notes](working-with-notes.md)
Creating, organizing, and using notes (both manual and AI-generated).

**Quick links:**
- Create a manual note
- Save AI responses as notes
- Apply transformations to generate insights
- Organize with tags and naming
- Use notes across your notebook

---

### 3. [Chat Effectively](chat-effectively.md)
Have conversations with AI about your sources. Manage context to control what AI sees.

**Quick links:**
- Start your first chat
- Select which sources go in context
- Ask effective questions
- Use follow-ups productively
- Understand citations and verify claims

---

### 4. [Creating Podcasts](creating-podcasts.md)
Convert your research into audio dialogue for passive consumption.

**Quick links:**
- Create your first podcast
- Choose or customize speakers
- Select TTS provider
- Generate and download
- Common audio quality fixes

---

### 5. [Search Effectively](search.md)
Two search modes: text-based (keyword) and vector-based (semantic). Know when to use each.

**Quick links:**
- Text search vs vector search (when to use)
- Running effective searches
- Using the Ask feature for comprehensive answers
- Saving search results as notes
- Troubleshooting poor results

---

### 6. [Transformations](transformations.md)
Batch-process sources with predefined templates. Extract the same insights from multiple documents.

**Quick links:**
- Built-in transformation templates
- Creating custom transformations
- Applying to single or multiple sources
- Managing transformation output

---

### 7. [Citations](citations.md)
Verify AI claims by tracing them back to source material. Understand the citation system.

**Quick links:**
- Reading and clicking citations
- Verifying claims against sources
- Requesting better citations
- Saving cited content as notes

---

### 8. [API Configuration](api-configuration.md)
Configure AI provider API keys directly through the Settings UI.

**Quick links:**
- Add API keys without editing files
- Test provider connections
- Migrate from environment variables
- Manage Azure and OpenAI-compatible providers
- Understand key storage and encryption

---

## Which Feature for Which Task?

```
Task: "I want to explore a topic with follow-ups"
→ Use: Chat (add sources, select context, have conversation)

Task: "I want one comprehensive answer"
→ Use: Search / Ask (system finds relevant content)

Task: "I want to extract the same info from many sources"
→ Use: Transformations (define template, apply to all)

Task: "I want summaries of all my sources"
→ Use: Transformations (with built-in summary template)

Task: "I want to share my research in audio form"
→ Use: Podcasts (create speakers, generate episode)

Task: "I want to find that quote I remember"
→ Use: Search / Text Search (keyword matching)

Task: "I'm exploring a concept without knowing exact words"
→ Use: Search / Vector Search (semantic similarity)

Task: "I need to add or change my AI provider API keys"
→ Use: Settings / API Keys (configure providers without editing files)
```

---

## Quick-Start Checklist: First 15 Minutes

**Step 1: Create a Notebook (1 min)**
- Name: Something descriptive ("Q1 Market Research", "AI Safety Papers", etc.)
- Description: 1-2 sentences about what you're researching
- This is your research container

**Step 2: Add Your First Source (3 min)**
- Pick one: PDF, web link, or text
- Follow [Adding Sources](adding-sources.md)
- Wait for processing (usually 30-60 seconds)

**Step 3: Chat About It (3 min)**
- Go to Chat
- Select your source (set context to "Full Content")
- Ask a simple question: "What are the main points?"
- See AI respond with citations

**Step 4: Save Insight as Note (2 min)**
- Good response? Click "Save as Note"
- Name it something useful ("Main points from source X")
- Now you have a captured insight

**Step 5: Explore More (6 min)**
- Add another source
- Chat about both together
- Ask a question that compares them
- Follow up with clarifying questions

**Done!** You've used the core workflow: notebook → sources → chat → notes

---

## Common Mistakes to Avoid

| Mistake | Problem | Fix |
|---------|---------|-----|
| Adding everything to one notebook | No isolation between projects | Create separate notebooks for different topics |
| Expecting AI to know your context | Questions get generic answers | Describe your research focus in chat context |
| Forgetting to cite sources | You can't verify claims | Click citations to check source chunks |
| Using Chat for one-time questions | Slower than Ask | Use Ask for comprehensive Q&A, Chat for exploration |
| Adding huge PDFs without chunking | Slow processing, poor search | Break into multiple smaller sources if possible |
| Using same context for all chats | Expensive, unfocused | Adjust context level for each chat |
| Ignoring vector search | Only finding exact keywords | Use vector search to explore conceptually |

---

## Next Steps

1. **Follow each guide** in order (sources → notes → chat → podcasts → search)
2. **Create your first notebook** with real content
3. **Practice each feature** with your own research
4. **Return to CORE-CONCEPTS** if you need to understand the "why"

---

## Getting Help

- **Feature not working?** → Check the feature's guide (look for "Troubleshooting" section)
- **Error message?** → Check [6-TROUBLESHOOTING](../6-TROUBLESHOOTING/index.md)
- **Understanding how something works?** → Check [2-CORE-CONCEPTS](../2-CORE-CONCEPTS/index.md)
- **Setting up for the first time?** → Go back to [1-INSTALLATION](../1-INSTALLATION/index.md)
- **For developers** → See [7-DEVELOPMENT](../7-DEVELOPMENT/index.md)

---

**Ready to start?** Pick the guide for what you want to do first!
