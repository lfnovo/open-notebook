# Citations - Verify AI Answers

Chat and Ask answers include references to the items they are based on, so you can check a claim against your own material.

---

## What a Citation Points To

The model is told to cite items by their record ID, such as `source:abc123`, `note:def456` or `insight:ghi789`. A citation always points to a **whole item**:

- a **source** (its full extracted text),
- a **note**, or
- an **insight** (a transformation's output for a source).

Citations don't carry page numbers, sections or highlighted passages. To find the exact place, open the item and look for the claim (your browser's find-in-page helps).

## Where You See Them

- **Notebook chat and source chat**: inline numbers like **[1]**, with a **References** list at the end of the answer. Click a number or a reference to open the item in a dialog.
- **Ask**: inline links in the answer; click one to open the item.

If a cited item was deleted after the answer was written, the dialog says *This content no longer exists*.

Transformations don't produce citations; an insight is the transformation's output for one known source.

---

## Checking a Claim

1. Click the citation next to the claim.
2. Read the opened item and find the supporting text.
3. If you can't find it, ask in the same chat: "Where exactly in that source does it say this? Quote the passage."

Things that make citations more reliable:

- **Ask for them.** "Cite the source for each claim" in your question.
- **Put the right content in context.** In notebook chat, a source at *Insights only* can only be cited through its title and insights. If you need claims backed by the full text, set it to *Full content*.
- **Prefer specific questions.** Broad summaries tend to cite less.

The model chooses what to cite, so a citation can be missing or point to the wrong item. Treat citations as a pointer to check, not as proof.

---

## Keeping Cited Answers

- **Save to note** (notebook chat) and **Save to Notebooks** (Ask) save the answer text, including its references. See [Working with Notes](working-with-notes.md).
- **Copy to clipboard** copies the answer text.

There is no export or share feature for citations.
