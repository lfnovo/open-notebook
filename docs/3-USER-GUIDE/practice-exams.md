# Practice Exams - Test Yourself on Your Sources

Practice exams turn a notebook into a self-assessment tool. The AI writes an exam from the notebook's sources (and, optionally, its notes); you answer it in the app and get a score plus feedback on every question.

---

## Quick Start: Your First Exam

```
1. Open a notebook and click "Create exam" (or go to Create → Exams → New Exam)
2. Pick the sources to use (all are selected by default)
3. Choose how many questions of each type you want
4. Pick a difficulty and, optionally, a language
5. Click "Generate exam" (usually 20 seconds to 2 minutes)
6. Answer the questions and click "Submit answers"
7. Review your score, the correct answers and the AI feedback
```

---

## Question Types

| Type | What you do | How it is graded |
|------|-------------|------------------|
| **Multiple choice** | Pick the one correct option out of four | Automatically, no AI call |
| **Multiple select** | Tick every correct option ("select all that apply"; 2 or more are correct) | Automatically, with partial credit: each correct pick earns its share of the points and each wrong pick cancels one correct pick, so ticking everything scores 0 |
| **Fill in the blank** | Type the missing term(s) in the sentence | Exact matches (ignoring case, accents and punctuation) are graded automatically; anything else is judged by the AI, which accepts synonyms and small typos and can give partial credit per blank |
| **Open answer** | Write an explanation in your own words | By the AI, against a reference answer and a rubric, with partial credit and written feedback |

Default points: 1 per multiple-choice and fill-in-the-blank question, 2 per multiple-select question; open questions are worth 3 (easy), 5 (medium) or 10 (hard).

---

## Exam Options

| Option | Notes |
|--------|-------|
| **Sources** | Only sources with extracted text are used. Very large selections are truncated to about 150k tokens |
| **Also use notes** | Adds the notebook's notes to the study material |
| **Questions per type** | 0–50 each, at most 50 in total |
| **Difficulty** | Easy, medium or hard |
| **Language** | Defaults to the language of the sources |
| **Extra instructions** | Free text for the exam writer, e.g. "focus on chapter 3" |
| **Model** | Used both to write the exam and to grade open answers. Defaults to your default transformation model |

---

## Taking and Reviewing an Exam

- The answer key is **not** sent to the browser while you take the exam; it is only loaded when you review a graded attempt.
- Unanswered questions score 0; the app warns you before submitting an incomplete exam.
- Every attempt is saved. Open an exam to see its attempts on the right, click one to review it, or click **Retake exam** to start over.
- Questions graded by the model are marked **Graded by AI**. Treat AI grades as study feedback, not as an authoritative mark: check the reference answer and the explanation when a grade looks wrong.

---

## Tips

- **Model choice matters for open answers.** Grading quality follows the model; smaller local models may be more lenient or less consistent.
- **Reasoning models are slower.** Generation with a reasoning model can take a couple of minutes for long exams.
- **Keep the material focused.** Selecting only the sources you are studying gives more relevant questions than a whole large notebook.

---

## API

Everything in the UI is available through the REST API (see `/docs` on the API port):

| Endpoint | Purpose |
|----------|---------|
| `POST /api/exams` | Generate an exam from a notebook |
| `GET /api/exams?notebook_id=` | List exams (with attempt count and best score) |
| `GET /api/exams/{id}?include_answers=` | Get an exam; the answer key only when `include_answers=true` |
| `DELETE /api/exams/{id}` | Delete an exam and its attempts |
| `POST /api/exams/{id}/attempts` | Submit answers and get them graded |
| `GET /api/exams/{id}/attempts` | List attempts |
| `GET` / `DELETE /api/exam-attempts/{id}` | Get or delete one attempt |

Answers are keyed by question id: the option index for multiple choice, a list of option indexes for multiple select, a list of strings (one per blank) for fill in the blank, and text for open answers.

## Images in questions

**Include images when useful** is enabled when creating an exam. The model can inspect selected sources, crop relevant figures, or generate an educational illustration if no suitable source figure is available. Images are included only when they help answer a question, for example when interpreting a chart or diagram. Answer sheets and solved exercises should not be used as figures.

Choose a model that supports vision and tools. Disable the option to generate a text-only exam. Image preparation may add generation time and provider charges.

Figures appear above the answer controls. Click a figure to enlarge it. The same saved image is available when reviewing results and is sent to the grading model for open questions and non-exact blank answers. Source links appear during review; captions and source filenames are hidden while answering to avoid giving away an answer. Existing exams continue to work without images.
