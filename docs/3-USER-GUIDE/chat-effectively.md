# Chat Effectively - Conversations with Your Research

Notebook chat is a conversation with an AI model about the sources and notes you put in context. This page covers how to use it. How the context is built, and how Chat differs from Ask, is explained in [AI Context & RAG](../2-CORE-CONCEPTS/ai-context-rag.md).

---

## Quick Start

1. Open a notebook. The **Chat with Notebook** column is on the right (on a phone, the **Chat** tab).
2. Check what's in context: the panel above the message box shows how many sources and notes are included and an estimated token count.
3. Type your question in **Ask anything about your sources...** and press **Ctrl+Enter** (**⌘+Enter** on Mac). Plain **Enter** adds a new line.
4. Click a numbered reference in the answer to open the source, note or insight it cites.

The first message creates a chat session automatically.

---

## Choosing What the AI Sees

Every source and note in the notebook has a context level. Chat sends the selected content with **every** message, so this is where you control quality, cost and what a cloud provider receives.

**Per item:** click the **context icon** on a source or note card to cycle through its levels. Hover it to see the current one.

| Level | Sources | Notes |
|-------|---------|-------|
| **Not included in chat** | Not sent | Not sent |
| **Insights only** | Title and insights (only offered when the source has insights) | — |
| **Full content** | Title, insights and full text | Title and content |

**All at once:** the **Context** menu in each column header.
- Sources: **Include all (insights only)** (sources without insights are left out), **Include all (full content)**, **Exclude all from context**.
- Notes: **Include all in context**, **Exclude all from context**.

Things to know:

- When you open a notebook, sources with insights start at *Insights only*, other sources at *Full content*, and notes are included.
- Your choices are **not saved**. Reloading the page resets them to the defaults.
- To make *Insights only* available for a source, generate an insight for it ([Transformations](transformations.md)).

**Choosing levels:**

- Use *Full content* for the few sources you are reading closely or quoting.
- Use *Insights only* for background sources. It's much smaller and usually enough for orientation.
- Exclude anything unrelated to the current question. Less noise gives better answers.
- If the context is very large (over about 105,000 tokens), Open Notebook switches to your **Large Context Model**.

---

## Sessions

A session is one conversation; its messages are saved and reloaded when you come back. Click **Sessions** to open **Chat Sessions**, where you can create a session (give it a title), switch to another one, rename it or delete it. Each session remembers the conversation, not the context selection.

## Choosing the Model

The model button next to the message box opens **Model Configuration**. Pick a model to use for this session instead of your **Chat Model** default, or click **Reset to Default**. Only language models you have added in **Manage → Models** are listed.

## Sending Images

Click **Attach images**, paste a screenshot into the message box, or drop images onto the composer. This works in both notebook chat and source chat. You can attach up to four PNG, JPEG or WebP images per message, at most 5 MB and 25 megapixels each. Click a preview to enlarge it, or remove an image before sending.

Add a question such as “Explain this chart using the selected sources,” or send the image on its own. Choose a model that supports images using the model selector. Images are sent to that model with your selected context and conversation history, saved with the session, and available in follow-up questions. If sending fails, the composer keeps the text and images so you can retry.

Chat attachments do not become sources and do not require Docling or OCR. To extract text from a scanned PDF and make it searchable, enable [Docling and OCR](content-processing-engines.md#ocr-toggle) and use **Retry Processing** on the failed source.

---

## Working With Answers

Under each AI answer:

- **Copy to clipboard** copies the answer text.
- **Save to note** saves it as an **AI Generated** note in this notebook, with a generated title. There is no dialog; the note appears in the Notes column.

**References** are the numbered links in the answer. They point to whole items (a source, note or insight), not to pages or passages. See [Citations](citations.md) for how to check them.

---

## Asking Good Questions

- **Be specific.** "What sample size and method did the 2024 survey use?" gets a better answer than "Tell me about the survey."
- **Name the sources** when several are in context: "Compare how the Smith paper and the OECD report define productivity."
- **Ask for the format you want:** a table, a bullet list, a short paragraph.
- **Ask for references** when you plan to verify: "Cite the source for each claim."
- **Follow up.** The model sees the whole session, so "Expand on the second point" works.

---

## Source Chat

Each source also has its own chat. Open the source and click **Chat with Sources**: the source page shows the content on the left and the chat on the right, with its own sessions and model choice.

Source chat always uses that source's full text and insights; there are no context levels. Long sources are truncated to fit about 50,000 tokens, so questions about the later parts of a very long document may not be answerable there; use notebook chat with the source at *Full content* instead (large contexts switch to your Large Context Model). **Save to note** is not available in source chat (the source isn't tied to one notebook); use **Copy to clipboard**.

---

## When Something Goes Wrong

| Symptom | What to do |
|---------|-----------|
| *The model returned an empty response...* | Retry, or pick another model. Reasoning models with a small output limit can spend everything on thinking. The failed question is not kept in the session, so retrying doesn't duplicate it |
| Answers ignore a source | Check its context icon; it may be excluded or at *Insights only* with thin insights |
| Slow or expensive | Reduce context: exclude sources, use *Insights only*, or start a new session (the whole session history is sent too) |
| *The AI provider took too long to respond...* | The request hit the backend timeout (`ESPERANTO_LLM_TIMEOUT`, 180 seconds by default). Retry, use a faster model, reduce context, or raise the timeout |
| *No model configured...* | Set the Chat Model in **Manage → Models → Default Model Assignments** |

More in [AI & Chat Issues](../6-TROUBLESHOOTING/ai-chat-issues.md).


## Images in answers

Request an image or source crop directly in notebook or source chat; this activates visual tools automatically. Enable **Visual responses** below the composer to let the assistant choose relevant source figures for other messages.
Choose a model that supports both vision and tool calling, such as GPT-4.1.

- For source images, ask: “Explain this chart and include a crop from the PDF.”
  The assistant searches the selected sources, previews the page, and crops the
  relevant region. Each crop links to its source and shows its page number.
- For generated images, ask explicitly: “Generate an illustration of the
  clustering methods described in these sources.” Generated images are labeled
  as illustrations; they are not source evidence.
- Click an image to enlarge it. Images and provenance are saved with the chat.

Crops support retained PDFs and PNG/JPEG/WebP source files, including scanned
PDFs. Deleted original files must be re-uploaded with file retention enabled.
Notebook crops are restricted to selected sources that belong to the notebook.
The assistant can attach up to four images and generate one new image per turn.

Image generation uses the selected OpenAI-compatible chat model's credential,
or `OPENAI_API_KEY`/`OPENAI_BASE_URL` when no linked account is available. Operators
can choose a separate saved OpenAI-compatible credential with
`OPEN_NOTEBOOK_IMAGE_CREDENTIAL_ID`. The default image model is `gpt-image-1.5`;
set `OPEN_NOTEBOOK_IMAGE_MODEL` to use another GPT Image model supported by the
provider. Requests use the [OpenAI Images API](https://developers.openai.com/api/reference/python/resources/images/methods/generate).
An account must support image generation; chat access alone does not guarantee it.
Provider failures are explained in the answer without attaching a fabricated image.

### Images in the explanation

With visual responses enabled, figures appear beside the relevant explanation instead of in a separate gallery at the end. Click an image to enlarge it; source crops retain their source and page link. Previously saved attachments remain visible.

### Practice inside the response

Ask for a short test, practice questions or a self-check. The assistant can also include a test when applying an explained concept would help learning. Answer the interactive card directly in the chat and select **Submit answers** to see your score, feedback and solutions. Use **Try again** to take another attempt. Saved results remain available after reloading the conversation.

Tests support single choice, multiple selection, blanks and open answers. Open answers are graded by AI. When a question needs a figure, its actual saved image is shown and used during grading. Ask directly for a source crop or a generated illustration for the test; you do not need to enable the visual responses checkbox. Requests for an exam or questionnaire also create an interactive test.

If the model produces a malformed test, the app tries to repair it automatically. If it cannot, your explanation and images remain available; you can ask the assistant to generate the test again.
