# Decision Records

The project's decision log: short, dated, immutable records of structural decisions. They answer *"why is it like this?"* months later, and prevent settled discussions from being reopened without knowing they were settled.

Two kinds, same format:

- **ADR** (Architecture Decision Record) — technical choices: `ADR-NNN-slug.md`
- **PDR** (Product Decision Record) — product direction and scope: `PDR-NNN-slug.md`

The **current rules** distilled from these records live in [VISION.md](../../../VISION.md) (product identity + posture) and [design-principles.md](../design-principles.md) (engineering practices). Records are the memory; those pages are the law.

## Rules

1. **Records are immutable.** Reversing a decision means writing a *new* record and marking the old one `Superseded by ADR-NNN` in its Status line — never editing history.
2. **Write it in the same PR.** A design that resolves an open structural question ships with its record. Half a page, written while the context is loaded — not a documentation session later.
3. **Keep it to half a page.** Four sections: Context, Decision, Alternatives considered, Consequences. If it needs more, link an issue or doc for the depth.
4. **Number sequentially** within each prefix (ADR-005 comes after ADR-004, independent of PDRs).

## Template

```markdown
# ADR-NNN: <Title>

- **Status**: Accepted | Superseded by ADR-NNN
- **Date**: YYYY-MM
- **Related**: #issue, other records

## Context
What was the situation and the forces at play? (2-5 sentences)

## Decision
What we decided, stated as a rule someone can follow.

## Alternatives considered
What else was on the table and why it lost. (bullets)

## Consequences
What this makes easier, what it makes harder, what to watch. (bullets)
```

## Index

| Record | Title | Status |
|---|---|---|
| [ADR-001](ADR-001-surrealdb.md) | SurrealDB as the database | Accepted |
| [ADR-002](ADR-002-external-libraries.md) | Delegate platform/media support to focused external libraries | Accepted |
| [ADR-003](ADR-003-streamlit-to-nextjs.md) | Migrate the UI from Streamlit to Next.js | Accepted |
| [ADR-004](ADR-004-background-workers.md) | Long-running work runs on background workers | Accepted |
| [PDR-001](PDR-001-single-user-first.md) | Single-user first; don't preclude multi-user | Accepted |
| [PDR-002](PDR-002-provider-agnostic-core.md) | Provider-agnostic core by default | Accepted |
