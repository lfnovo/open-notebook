# Transformations - Generating Insights from Sources

A **transformation** is a saved prompt that runs on one source. Its output is saved as an **insight** on that source, titled with the transformation's title. Insights show on the source's **Insights** tab, can be sent to Chat on their own (the *Insights only* context level), are used by the *Summary* option in podcasts, and are searchable. See [Notebooks, Sources, Insights, and Notes](../2-CORE-CONCEPTS/notebooks-sources-notes.md#insights).

---

## Running a Transformation

There are two places to run one.

**When you add a source.** Step 3 of the Add Source wizard (**Process**) lists your transformations under **Transformations (optional)**. Tick the ones you want; they run after the text is extracted. In a batch upload, the selection applies to every item. This is the way to apply a transformation to many sources at once.

**On an existing source.**

1. Open the source (click its card) and go to the **Insights** tab.
2. Under **Generate New Insight**, choose a transformation in **Select a transformation...**.
3. Click **New**. You'll see *Insight generation started. It will appear shortly.*

The transformation runs in the background and the insight appears on the tab when it's done. Running the same transformation again adds another insight; delete the ones you don't want (**View Insight** → **Delete**, or the delete icon on the insight).

There is no action to run a transformation on several existing sources at once.

---

## Built-in Transformations

A new install comes with six:

| Title | What it produces |
|-------|------------------|
| **Paper Analysis** | An analysis of a technical or scientific paper |
| **Key Insights** | Important insights and actionable items |
| **Dense Summary** | A rich, dense summary. Pre-selected for new sources |
| **Reflection Questions** | Questions to help explore the document further |
| **Table of Contents** | The topics the document covers |
| **Simple Summary** | A short summary |

You can edit or delete any of them.

---

## Managing Transformations

Go to **Manage → Transformations**. The **Transformations** tab lists them under **Custom Transformations**; a **Default** badge marks the ones suggested for new sources.

### Create or edit

Click **Create New** (or **Edit** on a card) and fill in:

| Field | Meaning |
|-------|---------|
| **Name** | Unique identifier, for example `key_topics` |
| **Title** | The name shown in the UI and given to the insights it creates (defaults to the name) |
| **Description** | What it does |
| **System Prompt** | The instructions. The source's full text is sent after them |
| **Model** | The model to use. **System Default** uses your **Transformation Model** default (or the Chat Model) |
| **Suggest by default on new sources** | Pre-selects it in the Add Source wizard |

Write the prompt with the source in mind: ask for a summary, a list, a table, or any structured output. The output is saved as Markdown.

### Test in the Playground

The **Playground** tab (or **Playground** on a card) lets you pick a transformation and a model, paste **Input Text**, and click **Run Transformation**. The output is shown but not saved anywhere, so it's a safe place to tune a prompt.

### Default Transformation Prompt

The **Default Transformation Prompt** box at the top of the Transformations tab is meant to be added to every transformation prompt. In v1.15.0 the text is saved but not applied when transformations run, so put shared instructions in each transformation's prompt instead.

---

## Errors

| Message | Cause |
|---------|-------|
| *This source has no text content to transform* / *Source has no text content* | Extraction produced no text (for example a failed link). Fix the source first |
| *The model reached its generation limit before completing the transformation...* | The output was cut off. Use a shorter prompt or a model with a larger output limit |
| *The model returned no usable text for the transformation...* | The model returned nothing, or only thinking content. Try another model |

When you run a transformation from the Insights tab and it fails, an error toast shows the reason and no insight is saved. If a transformation selected in the Add Source wizard fails, the source's processing job fails with it and the source shows **Failed** (see [When a Source Fails](adding-sources.md#when-a-source-fails)). Provider and model problems are covered in [Troubleshooting](../6-TROUBLESHOOTING/index.md).

---

## Tips

- **Keep summaries short if you chat with insights.** A source set to *Insights only* sends all its insights with every chat message.
- **One job per transformation.** "Key arguments" and "Open questions" as two transformations give cleaner insights than one prompt asking for both.
- **Large sources** over about 105,000 tokens are sent to your **Large Context Model**, regardless of the transformation's model.
