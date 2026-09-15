# Notebook–Source Documentation Truth Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Correct the core-concepts documentation so it accurately explains that a source is stored once, may be linked to multiple notebooks, and cannot be linked to the same notebook more than once.

**Architecture:** Treat `PRODUCT.md` as the product-truth authority and update only the stale conceptual guidance. Keep notebook organization, note ownership, permissions, and source deletion semantics distinct; this plan changes documentation only and does not substitute for the separate relationship-integrity backend plan.

**Tech Stack:** Markdown, ripgrep, existing repository documentation.

## Global Constraints

- Preserve the product truth in `PRODUCT.md:27,39,69`.
- A source may be linked to multiple different notebooks without re-uploading or duplicating the source.
- The same source may have at most one relationship to the same notebook.
- Removing a source from one notebook removes only that association; deleting the source globally affects every notebook using it.
- Do not claim notebook isolation means source records are duplicated or exclusive.
- Do not change application code, database schema, or runtime behavior in this task.

---

### Task 1: Reconcile the core-concepts guide with current product truth

**Files:**
- Modify: `docs/2-CORE-CONCEPTS/notebooks-sources-notes.md:46-51,104-112,205-213,256-268,272-278`
- Verify: `PRODUCT.md:27,39,69`

**Interfaces:**
- Consumes: the authoritative source/notebook relationship and deletion semantics in `PRODUCT.md`.
- Produces: one internally consistent core-concepts guide with no obsolete single-notebook or re-upload guidance.

- [x] **Step 1: Capture the stale statements before editing**

  Run:

  ```powershell
  rg -n -i "never appear|exactly one notebook|one notebook per source|tied to one notebook|re-upload|one notebook" docs/2-CORE-CONCEPTS/notebooks-sources-notes.md
  ```

  Expected before the edit: matches include the isolation paragraph, `Scoped` property, `One Notebook Per Source` decision, common-question answers, and summary table.

- [x] **Step 2: Replace the isolation and scope explanations**

  State that notebooks provide organizational and conversational context, while a source record can be reused across notebooks. Replace the `Scoped` property with this exact rule:

  ```markdown
  **Reusable**: A source is stored once and can be linked to multiple notebooks. Each notebook uses the same source as part of its own research context.
  ```

- [x] **Step 3: Replace the obsolete design decision**

  Rename `One Notebook Per Source` to `Reusable Sources, Explicit Notebook Associations` and explain all four consequences:

  - one source may be linked to several notebooks;
  - the same source cannot be linked twice to one notebook;
  - unlinking affects only the selected notebook association;
  - global source deletion affects every notebook that uses it.

- [x] **Step 4: Correct the common questions and summary**

  Replace instructions to re-upload or manually copy a source with instructions to add the existing source to another notebook. Change the source scope in the summary table from `One notebook` to `Independent; reusable across notebooks`. Preserve notebook-owned note semantics unless separately contradicted by verified implementation.

- [x] **Step 5: Verify no obsolete relationship claims remain**

  Run:

  ```powershell
  rg -n -i "never appear|exactly one notebook|one notebook per source|tied to one notebook|re-upload|scope.*one notebook" docs/2-CORE-CONCEPTS/notebooks-sources-notes.md
  ```

  Expected: no matches that claim a source is exclusive to one notebook or must be uploaded again.

  Run:

  ```powershell
  rg -n "multiple notebooks|stored once|Removing it from a notebook|deleting it globally" PRODUCT.md docs/2-CORE-CONCEPTS/notebooks-sources-notes.md
  ```

  Expected: both documents describe reusable sources and distinguish unlinking from global deletion.

- [ ] **Step 6: Commit the documentation correction**

  ```bash
  git add docs/2-CORE-CONCEPTS/notebooks-sources-notes.md
  git commit -m "docs: correct notebook source relationship guidance"
  ```
