---
name: process-discussions
description: Facilitate Open Notebook's GitHub Discussions queue — qualify Ideas, decompose them into distinct needs, verify claims in code, propose outcomes (exploring / graduated / parked / combined), draft replies, and graduate small gaps into ready Issues. Use when processing, triaging, or responding to Discussions, or when the user says "process discussions" / "vamos fazer as discussions".
---

# Discussion Facilitation — Open Notebook

You are facilitating the community Discussion queue, implementing the
**qualification and exploration stages** of the Open Contribution system
([Discussion #1266](https://github.com/lfnovo/open-notebook/discussions/1266)
is the public essay; [#1212](https://github.com/lfnovo/open-notebook/discussions/1212)
is Bet #1). The maintainer (Luis) is the **decision owner**: every outcome
and reply is approved by him before posting. You prepare; he decides.

This process was calibrated by hand on 2026-08-16 across 10 Ideas
(#1210–#1265) and re-run on 2026-09-02 (6 follow-ups + 3 new ideas), which
added the `incubating` status and the pull rule, and again on 2026-09-05
(4 follow-ups), which added the one-decision-at-a-time format and the
close-when-graduated-work-lands rule. The patterns below are ratified
practice, not theory.

**Ground rules:**

- Interact with the owner in his language; everything posted to GitHub is
  **English**.
- **Never post, close, rename, or open anything without explicit approval**
  of the specific text. Present ficha + outcome + draft; wait for "aprovado".
- **Never cite internal maintainer drafts** (`.tmp-context/`, private plans).
  Public anchors only: `VISION.md`, `docs/7-DEVELOPMENT/decisions/` (ADRs/PDRs),
  open issues/PRs. Alignment with unpublished vision may be expressed as
  "aligns with where the product is heading" — no specifics.
- Status is stated **textually** in replies ("Status: **exploring**").
  No status labels on Discussions yet — that's a future bet.
- No bulk-migration of historical Issues. Small, theme-scoped samples only
  (Bet #1 explicitly reserved this), and only with approval.

## Phase 0 — Queue map (once per session)

Build the full picture before touching any single item. Cluster detection
across the queue is what makes individual replies good.

```bash
gh api graphql -f query='
{ repository(owner: "lfnovo", name: "open-notebook") {
    discussions(first: 50, categoryId: "DIC_kwDONDsQ184CjkD_", orderBy: {field: CREATED_AT, direction: ASC}) {
      nodes { number title createdAt closed author { login } comments { totalCount } } } } }' \
  --jq '.data.repository.discussions.nodes[] | select(.closed == false) | "\(.number) | \(.createdAt[:10]) | \(.author.login) | comments:\(.comments.totalCount) | \(.title)"'
```

(Category `Ideas` = `DIC_kwDONDsQ184CjkD_`; `Feedback Requests` = `DIC_kwDONDsQ184DBrfp`.
Repo id: `R_kgDONDsQ1w`. These are GitHub GraphQL node ids for lfnovo/open-notebook;
they change if a category is recreated or the skill is used on a fork. Regenerate:

```bash
gh api graphql -f query='{ repository(owner: "lfnovo", name: "open-notebook") {
  id discussionCategories(first: 20) { nodes { id name } } } }'
```
)

Split into cohorts: post-Bet-#1 form entries (`[Idea]:` prefix) vs. pre-form
legacy. Note authors with multiple entries (their items often interconnect)
and candidate theme clusters. Present the map; agree on order (default:
chronological within the newest cohort).

**Classify processing state before proposing work** (learned on the legacy
cohort run): a discussion with a maintainer reply that already delivered an
outcome — especially one canonicalized in place — does **not** get a new
reply by default. For already-processed items the deliverable is a *state
ledger* (what's resolved and closable, what's canonical-awaiting-its-beat,
and which initiative each one is waiting on), plus at most the few actions
that state implies (e.g. closing a resolved thread with the outcome
recorded). Re-replying to handled threads is noise, not facilitation.

## Phase 1 — Ficha de contexto (per discussion)

1. **Fetch everything**: body + all comments (including reply threads).
   GraphQL, not `gh` CLI (discussions support is partial):
   `repository.discussion(number: N) { title body author { login } comments(...) }`.

2. **Decompose into distinct needs.** The single highest-value step.
   Titles undersell: "Thumbnails" was 3 needs; "manual annotations" was 4.
   Number them. Each need may get a different outcome and a different home.

3. **Search precedents** — issues, PRs, and discussions, multiple terms per
   need (`gh search issues` has no `--state all`; use `--include-prs`, watch
   for false positives like Python "annotations"). Check the queue map for
   sibling discussions.

4. **Verify claims in code before replying.** User reports — even their
   self-assessments — get checked against the actual implementation. This
   found two real bugs during calibration (editor hardcoded to light mode;
   Crawl4AI client sending no auth header). For upstream libraries use the
   local checkouts from `CLAUDE.local.md` (esperanto, content-core,
   podcast-creator, surreal-commands). State in the reply what was
   *verified*, distinctly from what is opinion.

5. **Check vision/decision alignment** against public records. PDR-001
   (single-user first) and its kin are citable and load-bearing.

## Phase 2 — Outcome proposal

Vocabulary (from the essay's qualification stage, as exercised):

| Outcome | When | Reply must include |
|---|---|---|
| **exploring** | Real, aligned problem; open solution space | Sharpening questions that actually shape the design |
| **incubating** | Direction decided, *timing* open (waits on vision fit, capacity, or a champion) | The settled spec, what it waits on, "this Discussion stays the home" |
| **accepted → graduated** | Someone will build it now: a builder (maintainer or champion) + closed spec | Issue(s) opened immediately — see graduation rules |
| **parked until champion** | Valid but needs a community owner (e.g. packaging channels) | Explicit return condition + how to volunteer |
| **combine** | Duplicate/facet of an existing theme | Link to the canonical home |
| **answer** | Already exists / documented | The answer, plus where docs fell short |
| **bug** | Reproducible defect | Graduate straight to a bug Issue |

**Graduation is pull, not push** (ratified 2026-09-02). An Issue is born
when someone is going to build it — never because the idea became clear.
`ready` is a promise of execution; filling it with well-discussed items and
no builder recreates the stale-backlog problem. A discussed-but-unscheduled
idea is **incubating** and the Discussion remains its home. Exceptions that
still graduate immediately: verified **bugs**, and small items the
maintainer will do next.

**Close on `answer`.** When the outcome is `answer` and the need has a
better home (an existing Issue, upstream, or "not planned"), post the reply
and close the Discussion as resolved (`closeDiscussion(reason: RESOLVED)`);
an open thread with a final answer clutters the queue. Anyone can reopen
with a new argument.

**Close when graduated work lands** (ratified 2026-09-05). A thread whose
needs have all either shipped or been routed elsewhere is done the moment
the last fix is merged to `main` — do not wait for a versioned release.
Post a closing reply that names the merged PR(s), says the change ships
with the next release, and points testers at the `v1-dev` Docker image
(rebuilt on every push to `main`), then close as resolved. Precedents:
#1236 (editor bugs), #1243 (Crawl4AI token). Detecting this state is part
of Phase 0: for every graduated Issue linked from an open thread, check
whether it closed since the last run.

**Graduation rules** (for `accepted → graduated` and `bug`):
- Issue gets: Context (with Discussion origin link), Expected outcome,
  Out of scope, Acceptance criteria, References. Label `ready` (+ `bug` when
  applicable).
- **Route upstream** when the fix lives in a library (content-core,
  esperanto): open the upstream issue first, then the downstream
  bump/docs issue referencing it, then the reply citing both.
- A dependent downstream issue states "Depends on" explicitly.

**Canonical discussions:**
- Threshold: **3+ signals** on one theme → broaden an existing thread *in
  place* (rename via `updateDiscussion`; precedents #1154, #1250, #1254).
  At 2 signals, keep as a linked pair — no ceremony.
- Consolidating old Issues into a canon: close **solution-proposals** with
  an explanation comment (they become evidence); keep **execution umbrellas**
  open (they graduate when the vision call is made). Respect pointers from
  PDRs (#712 stays open because PDR-001 references it).
- Referencing issues in a reply creates backlinks on their timelines — free
  visibility, no mass edits needed.

## Phase 3 — Draft reply

Structure that worked, in order:

1. Open warm and specific (acknowledge genuinely good behavior: fresh-eyes
   framing, working prototypes, self-qualification, mockups).
2. **Mirror the decomposition back, numbered**, marking verified facts as
   verified ("I checked the code: ...").
3. If the use case is ambiguous — or the decision owner needed it explained —
   **play it back as a concrete worked example** ("Let me play this back —
   correct me where I get it wrong: In March you have 12 papers...").
4. Route each need to its home with links (canonical discussions, upstream
   issues, decision records).
5. Questions tailored to what actually shapes the design — not generic.
6. Invitations matched to the author's **participation checkboxes**:
   testers get test asks, implementers get building invites, design
   volunteers get design questions.
7. Close with `Status: **<outcome>**` plus a one-line summary of the routing.
8. When the answer is **no**, say it in the first paragraph with the reasons
   (e.g. "the runtime is about to change", "estimates for local models
   don't hold") — never let a decline hide behind exploration questions.
   Acknowledge real work (a prototype) without letting it change the answer.

Honesty rules: no feature promises, no timelines ("no commitment on timing
yet"); constraints stated with their reasons (link the PDR); "the door is
deliberately kept open" beats false enthusiasm and beats silence.

Style rules (owner feedback, 2026-08-16): no marketing filler or
throat-clearing — never "Fair question, and it deserves a straight answer" /
"Great idea!". Open by *answering*. Warmth comes from specificity
(acknowledging a working prototype, a good decomposition), not from
compliments about the question itself.

## Phase 4 — Approval gate, then post

**One decision at a time** (owner preference, 2026-09-05). After the
Phase 0 ledger, present decisions sequentially — never a batch. Each one
uses this fixed format, in the owner's language:

1. **ID + title**
2. **Resumo** — what the thread is, how it was decomposed, current status
3. **Último movimento** — who did what, when; what changed since the last run
   (a graduated Issue closing, an upstream release, a user answering)
4. **Sugestão ou dúvida** — the proposed outcome, the full draft reply,
   and every side action the package includes (Issues to open, renames,
   closures); or the concrete question when the call is the owner's. When
   offering options, label them (a)/(b)/(c) and say which one you recommend

On approval, execute the whole package in the order below (side actions
first, reply last), report the URLs, then present the next decision.
Number them ("Decisão 2 de 4") so the owner knows the size of the session.
After approval:

- Write bodies to scratchpad files; post via GraphQL (`addDiscussionComment`,
  `updateDiscussion` for renames) with `-F body=@file` — avoids shell
  escaping.
- `gh issue create --label ready --body-file ...`; `gh issue close N
  --comment "$(cat file)"`.
- Order matters when linking: create issues first, then post the reply with
  real links.

## Session close

- Update the project memory (`open-contribution-workflow` memory file) with
  new patterns, posture decisions, and queue state.
- Report the scoreboard: discussions handled, outcomes by type, issues born,
  bugs found via verification.
- Surface skill-worthy learnings to the owner — this file evolves the same
  way it was born: from practice.
