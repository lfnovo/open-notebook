# ADR-006: Migration granularity follows merge granularity, not release granularity

- **Status**: Accepted
- **Date**: 2026-07
- **Related**: #1085 (first case decided under this policy), #1031 (surreal-basics migration runner — policy carries over), [change-playbooks.md](../change-playbooks.md) (Database Migration playbook)

## Context

Multiple issues in the same release cycle can each need a schema migration. The intuitive worry: merging them one by one produces several small migrations (19, 20, 21, 22…) inside a single release, which "feels" messier than one consolidated migration per release.

Two facts about this project shape the decision:

1. Migrations run **automatically at API startup**, in sequence, tracked in `_sbl_migrations`. Users upgrading across any version span run all pending migrations transparently — they never see the count.
2. A `v1-dev` image is published on **every push to main**. A migration is therefore effectively *released the moment it lands on main* — dev-image users apply it immediately, before any versioned release exists.

## Decision

**One migration per PR that needs one; numbers allocated in merge order; never consolidate after a migration has touched main.**

- Each migration lives in the PR that motivates it, with its `_down` counterpart, reviewed together with the code that requires it.
- Multiple small migrations per release is the normal, healthy state — not a smell.
- Consolidation is only allowed **before merge**, as a development-time choice: when two in-flight PRs touch the *same table*, coordinate them (stack the PRs, or fold the schema change into the first one to land).
- Branch protection's strict mode makes number collisions between parallel PRs surface as a required update-branch before merge; renumbering is part of that rebase.

## Alternatives considered

- **One consolidated migration per release** — rejected: post-hoc squashing breaks every `v1-dev` user whose `_sbl_migrations` already recorded the individual migrations, and it decouples schema changes from the PRs that explain them.
- **Batch migrations in a release branch** — rejected for the same dev-image reason, plus it would hold merged features hostage to release timing.

## Consequences

- Release notes may list several migrations; that is an implementation detail, not a user-facing cost.
- Debugging stays cheap: "migration 21 broke it" is bisectable; a slice of a consolidated release migration is not.
- If parallel batches make number collisions frequent, add a cheap CI check (duplicate or gapped numbers fail the build).
- When the migration runner moves to surreal-basics (#1031), this policy transfers unchanged — it is about granularity and immutability-after-main, not about the runner.
