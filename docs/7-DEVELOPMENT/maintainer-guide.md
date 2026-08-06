# Maintainer Guide

This guide is for project maintainers to help manage contributions effectively while maintaining project quality and vision.

## Table of Contents

- [Discussion Management](#discussion-management)
- [Issue Management](#issue-management)
- [Pull Request Review](#pull-request-review)
- [Merging PR Batches](#merging-pr-batches)
- [Common Scenarios](#common-scenarios)
- [Communication Templates](#communication-templates)

## Discussion Management

Discussions are the intake and deliberation space for feature requests, ideas,
behavior changes, product direction, design, architecture, and contribution
proposals. An accepted idea becomes an Issue only when it is sufficiently clear
to track and execute.

### When a New Idea Discussion Is Created

**1. Initial triage** (within 24-48 hours when possible)

- Confirm that it is an idea or open-ended proposal rather than a reproducible bug.
- Search Discussions, Issues, PRs, `VISION.md`, and decision records for related context.
- Merge the signal into a canonical Discussion when the topic already exists; preserve links to the original author and contribution.
- Replace `needs-triage` with `needs-vision` when the question is *whether/why* the project should pursue it, or `needs-design` when the problem is wanted but the *how* remains open.

**2. Shape the conversation**

Ask for missing evidence rather than an implementation plan by default:

- What is the user trying to accomplish?
- What is difficult today, and how do they work around it?
- Who else has the same use case?
- Which constraints, alternatives, or failure modes matter?
- How would we validate that the outcome is better?

For larger proposals, keep a synthesis in the Discussion body or a maintainer
comment: what is known, what remains open, alternatives, and the decision owner.

**3. Close the loop**

Every mature Discussion ends with an explicit outcome:

- **Accepted:** create one or more scoped Issues from the Discussion, replace inherited discovery labels with `ready`, link them in both directions, and close the Discussion as resolved.
- **Experiment:** describe the bounded experiment and the evidence needed before a commitment.
- **Parked:** state why it is not timely and what condition would reopen it.
- **Declined:** explain the conflict with vision, scope, or maintenance cost.
- **Superseded/duplicate:** link the canonical Discussion or initiative.

Creating an Issue is the graduation event: it means the project has committed to
track executable work, not merely that the idea received positive reactions.

## Issue Management

### When a New Issue Is Created

**1. Initial triage** (within 24-48 hours when possible)

- Public Issues arrive through the bug or installation forms with `needs-triage`.
- Maintainers also create Issues when accepted Discussions graduate into executable work.
- Add one **type** and one **area** label where they apply (see [Labels](#labels)).

Quick assessment:

- Is it a reproducible bug or an already approved work item?
- Does it duplicate an existing Issue?
- Does it need more reproduction details or environment information?
- If it is an idea, feature request, or open-ended proposal, convert it to a Discussion and explain the workflow.

**2. Initial response**

```markdown
Thanks for opening this issue! We'll review it and get back to you soon.

[If it's a bug] In the meantime, have you checked our troubleshooting guide?
```

**3. Bug triage**

Ask yourself:

- Can it be reproduced from the supplied steps and environment?
- Is more information required from the reporter?
- Is it already fixed, a duplicate, or rooted in an upstream dependency?
- Is the expected behavior actually a product/design decision? If so, open or link a Discussion before defining the fix.

**4. Issue assignment**

If the contributor checked "I am a developer and would like to work on this":

**For triaged Issues:**

```markdown
Thanks for the clear report. We've confirmed this as work the project should track.

I see you'd like to work on this. Before you start:

1. Please share your proposed approach/solution
2. Review our [Contributing Guide](contributing.md) and [VISION.md](../../VISION.md)
3. Once we agree on the approach, I'll assign this to you

Looking forward to your thoughts!
```

**For Issues needing clarification:**

```markdown
Thanks for offering to work on this! Before we proceed, we need to clarify a few things:

1. [Question 1]
2. [Question 2]

Once we have these details, we can discuss the best approach.
```

**For an idea opened as an Issue:**

```markdown
Thank you for the proposal! We use GitHub Discussions for feature requests,
product/design/architecture ideas, and contribution proposals so the community
can explore them before they become implementation commitments.

I'm converting this Issue to a Discussion. If the direction is accepted and
sufficiently scoped, we'll create an approved Issue from it before implementation.
```

### Labels

The label set is curated — **don't invent labels**. If something doesn't fit, raise it instead of adding one. Assign **one state**, **one type**, and **one area** where each applies; multiple bundling/ecosystem labels are fine.

**Discovery states** — primarily used on Discussions. Historical Issues may retain
these while the backlog is migrated; do not newly route feature proposals into Issues:

| Label | Meaning |
|---|---|
| `needs-triage` | New signal not yet classified |
| `needs-vision` | Unsure if/how this fits — strategic call for the maintainers (against [VISION.md](../../VISION.md)) |
| `needs-design` | Wanted, but the *how* isn't resolved — needs design/spec before it's ready |

**Issue delivery states:**

| Label | Meaning |
|---|---|
| `needs-triage` | New bug or installation report not yet triaged |
| `needs-info` | Waiting on the reporter to confirm or provide more information |
| `ready` | Approved and sufficiently specified — the dev loop can pick it up |
| **Close** | Use GitHub's native close reasons (duplicate / not planned); link the canonical issue when duplicate/superseded |

**Type** — what kind of work it is (apply one when clear):
- `bug` · `enhancement` · `documentation`
- `installation` is an intake label applied by the issue-creation workflow (not by triage); installation reports get routed to `area: deploy`.

**Area** — which part of the system (apply always, one per issue):

| Label | What goes here |
|---|---|
| `area: chat` | Conversation/chat, RAG retrieval, agentic responses, citations |
| `area: search` | Full-text and semantic search |
| `area: sources` | Source ingestion & processing (URLs, files, extraction, chunking) |
| `area: notebooks` | Notebook features: notes, insights, transformations |
| `area: providers` | AI provider integrations + model configuration |
| `area: embeddings` | Embedding models, vectorization, semantic indexing |
| `area: podcast` | Podcast / audio generation |
| `area: database` | SurrealDB, persistence, schema, migrations |
| `area: ui` | Frontend (Next.js), UX, visual issues |
| `area: deploy` | Docker, deployment, k8s, reverse proxy, infra/setup |
| `area: offline` | Airgapped/offline operation |
| `area: i18n` | Internationalization / localization |

**Bundling / epics:**
- `umbrella` — a tracking issue grouping related work
- `tracked-in-umbrella` — covered by an umbrella; follow the umbrella for progress
- `bundled` — part of a thematic bundle
- `upstream` — root cause lives in one of our libraries, not this repo

**Ecosystem** — issues whose real home is an upstream library:
- `esperanto` (model abstraction) · `content-core` (content extraction) · `podcast-creator` (podcast generation)

**Community:**
- `good first issue` — small, well-scoped, newcomer-friendly
- `help wanted` — we'd welcome a contributor to take this

### Consolidation: Discussion vs. umbrella

When several open issues circle the same topic, pick the model by **how decided the work is** — not just by shared theme:

- **Pre-vision / pre-design topic** → create or select **one canonical Discussion**, capture each request's signal (👍 counts, interested contributors) in its synthesis, and convert/link the related Issues or Discussions to it. A topic isn't N work items — it's one thinking space.
- **Already decomposed into real parallel tasks** → use `umbrella` + `tracked-in-umbrella`. Children stay open because each is independently pickable (e.g. the multi-user umbrella #712).

Rule of thumb: if work cannot start until *we* make a call, it belongs in a Discussion. If the call is made and the work splits into things a contributor could pick up today, it belongs in an umbrella with child Issues. **Never convert or close an Issue that has an active assignee/contributor or open PR without coordinating with them** — link it as a phase instead.

## Pull Request Review

### Initial PR Review Checklist

**Before diving into code:**

- [ ] Is there an associated approved Issue?
- [ ] Does the PR reference the issue number?
- [ ] Is the PR description clear about what changed and why?
- [ ] Did the contributor check the relevant boxes in the PR template?
- [ ] Are there tests? Screenshots (for UI changes)?

**Red Flags** (may require closing PR):
- No associated approved Issue on a non-trivial change (small obvious fixes are exempt; sizeable PRs should become drafts while an idea goes through Discussion or a bug goes through Issue triage)
- Issue was not assigned to contributor
- PR tries to solve multiple unrelated problems
- Breaking changes without discussion
- Conflicts with project vision

### Code Review Process

**1. High-Level Review**

- Does the approach align with our architecture?
- Is the solution appropriately scoped?
- Are there simpler alternatives?
- Does it follow our design principles?

**2. Code Quality Review**

Python:
- [ ] Follows PEP 8
- [ ] Has type hints
- [ ] Has docstrings
- [ ] Proper error handling
- [ ] No security vulnerabilities

TypeScript/Frontend:
- [ ] Follows TypeScript best practices
- [ ] Proper component structure
- [ ] No console.logs left in production code
- [ ] Accessible UI components

**3. Testing Review**

- [ ] Has appropriate test coverage
- [ ] Tests are meaningful (not just for coverage percentage)
- [ ] Tests pass locally and in CI
- [ ] Edge cases are tested

**4. Documentation Review**

- [ ] Code is well-commented
- [ ] Complex logic is explained
- [ ] User-facing documentation updated (if applicable)
- [ ] API documentation updated (if API changed)
- [ ] Migration guide provided (if breaking change)

### Providing Feedback

**Positive Feedback** (important!):
```markdown
Thanks for this PR! I really like [specific thing they did well].

[Feedback on what needs to change]
```

**Requesting Changes:**
```markdown
This is a great start! A few things to address:

1. **[High-level concern]**: [Explanation and suggested approach]
2. **[Code quality issue]**: [Specific example and fix]
3. **[Testing gap]**: [What scenarios need coverage]

Let me know if you have questions about any of this!
```

**Suggesting Alternative Approach:**
```markdown
I appreciate the effort you put into this! However, I'm concerned about [specific issue].

Have you considered [alternative approach]? It might be better because [reasons].

What do you think?
```

## Merging PR Batches

Mechanics for landing a batch of approved PRs without stepping on each other:

- **Squash-merge everything.** One commit per PR keeps `main` linear and makes reverts trivial.
- **Expect CHANGELOG conflicts.** Every PR adds a bullet under `[Unreleased]`, so the Nth merge often flips its siblings to DIRTY. Resolve by rebasing the branch onto `main` and keeping **both** sides' bullets — they're independent entries, not competing edits — then `git push --force-with-lease`.
- **Contributor forks:** rebase the fork's branch onto `origin/main`, skipping commits that are already upstream, and push with an explicit-OID lease: `git push --force-with-lease=<branch>:<headOID>`. This works whenever the contributor left "Allow edits by maintainers" (maintainerCanModify) enabled.
- **Check for scheduled replacements first.** Before merging a fix into code that's slated to be replaced (e.g. the database layer migrating to surreal-basics, issue #1031), redirect the fix upstream or note it on the tracking issue instead of landing it in code that's about to disappear.
- **Hunt for competing PRs.** Before merging a fix, search open PRs for others addressing the same bug — pick the best one and close the rest with a link, rather than merging the first one you review.

## Common Scenarios

### Scenario 1: Good Code, Wrong Approach

**Situation**: Contributor wrote quality code, but solved the problem in a way that doesn't fit our architecture.

**Response:**
```markdown
Thank you for this PR! The code quality is great, and I can see you put thought into this.

However, I'm concerned that this approach [specific architectural concern]. In our architecture, we [explain the pattern we follow].

Would you be open to refactoring this to [suggested approach]? I'm happy to provide guidance on the specifics.

Alternatively, if you don't have time for a refactor, I can take over and finish this up (with credit to you, of course).

Let me know what you prefer!
```

### Scenario 2: PR Without Assigned Issue

**Situation**: Contributor submitted a non-trivial PR without an approved and assigned Issue.

**Response:**
```markdown
Thanks for the PR! I appreciate you taking the time to contribute.

However, to maintain project coherence, we require non-trivial PRs to be linked to an approved Issue that was assigned to the contributor. Small obvious fixes remain exempt. This is explained in our [Contributing Guide](contributing.md).

This helps us:
- Ensure work aligns with project vision
- Prevent duplicate efforts
- Discuss approach before implementation

Could you please:
1. Mark this PR as draft
2. Start a Discussion if this is a feature/design proposal, or an Issue if it fixes a reproducible bug
3. Wait for an approved Issue to be scoped and assigned
4. We can then continue with this PR

Sorry for the inconvenience - this process helps us manage the project effectively.
```

### Scenario 3: Idea Discussion Not Aligned with Vision

**Situation**: Well-intentioned feature that doesn't fit project goals.

**Response:**
```markdown
Thank you for this suggestion! I can see how this would be useful for [specific use case].

After reviewing against our [vision and principles](https://github.com/lfnovo/open-notebook/blob/main/VISION.md), we've decided not to include this in the core project because [specific reason - e.g., "it conflicts with our 'Simplicity Over Features' principle" or "it would require dependencies that conflict with our privacy-first approach"].

Some alternatives:
- [If applicable] This could be built as a plugin/extension
- [If applicable] This functionality might be achievable through [existing feature]
- [If applicable] You might be interested in [other tool] which is designed for this use case

We appreciate your contribution and hope you understand. Feel free to check our roadmap or open issues for other ways to contribute!
```

### Scenario 4: Contributor Ghosts After Feedback

**Situation**: You requested changes, but contributor hasn't responded in 2+ weeks.

**After 2 weeks:**
```markdown
Hey there! Just checking in on this PR. Do you have time to address the feedback, or would you like someone else to take over?

No pressure either way - just want to make sure this doesn't fall through the cracks.
```

**After 1 month with no response:**
```markdown
Thanks again for starting this work! Since we haven't heard back, I'm going to close this PR for now.

If you want to pick this up again in the future, feel free to reopen it or create a new PR. Alternatively, I'll mark the issue as available for someone else to work on.

We appreciate your contribution!
```

Then:
- Close the PR
- Unassign the issue
- Add `help wanted` label to the issue

### Scenario 5: Breaking Changes Without Discussion

**Situation**: PR introduces breaking changes that weren't discussed.

**Response:**
```markdown
Thanks for this PR! However, I notice this introduces breaking changes that weren't discussed in the original issue.

Breaking changes require:
1. Prior discussion and approval
2. Migration guide for users
3. Deprecation period (when possible)
4. Clear documentation of the change

Could we discuss the breaking changes first? Specifically:
- [What breaks and why]
- [Who will be affected]
- [Migration path]

We may need to adjust the approach to minimize impact on existing users.
```

## Communication Templates

### Closing a PR (Misaligned with Vision)

```markdown
Thank you for taking the time to contribute! We really appreciate it.

After careful review, we've decided not to merge this PR because [specific reason related to design principles].

This isn't a reflection on your code quality - it's about maintaining focus on our core goals as outlined in [VISION.md](https://github.com/lfnovo/open-notebook/blob/main/VISION.md).

We'd love to have you contribute in other ways! Check out:
- Good first issues
- Help wanted issues
- Our roadmap

Thanks again for your interest in Open Notebook!
```

### Closing a Stale Issue

```markdown
We're closing this issue due to inactivity. If this is still relevant, feel free to reopen it with updated information.

Thanks!
```

### Asking for More Information

```markdown
Thanks for reporting this! To help us investigate, could you provide:

1. [Specific information needed]
2. [Logs, screenshots, etc.]
3. [Steps to reproduce]

This will help us understand the issue better and find a solution.
```

### Thanking a Contributor

```markdown
Merged!

Thank you so much for this contribution, @username! [Specific thing they did well].

This will be included in the next release.
```

## Best Practices

### Be Kind and Respectful

- Thank contributors for their time and effort
- Assume good intentions
- Be patient with newcomers
- Explain *why*, not just *what*

### Be Clear and Direct

- Don't leave ambiguity about next steps
- Be specific about what needs to change
- Explain architectural decisions
- Set clear expectations

### Be Consistent

- Apply the same standards to all contributors
- Follow the process you've defined
- Document decisions for future reference

### Be Protective of Project Vision

- It's okay to say "no"
- Prioritize long-term maintainability
- Don't accept features you can't support
- Keep the project focused

### Be Responsive

- Respond to new Discussions and Issues within 48 hours when possible (even just to acknowledge)
- Review PRs within a week when possible
- Keep contributors updated on status
- Close stale issues/PRs to keep things tidy

## When in Doubt

Ask yourself:
1. Does this align with our [vision and principles](../../VISION.md)?
2. Will we be able to maintain this feature long-term?
3. Does this benefit most users, or just an edge case?
4. Is there a simpler alternative?
5. Would I want to support this in 2 years?

If you're unsure, it's perfectly fine to:
- Ask for input from other maintainers
- Start or link a GitHub Discussion
- Sleep on it before making a decision

---

**Remember**: Good maintainership is about balancing openness to contributions with protection of project vision. You're not being mean by saying "no" to things that don't fit - you're being a responsible steward of the project.
