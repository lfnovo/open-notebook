# PDR-001: Single-user first; new features must not preclude multi-user

- **Status**: Accepted
- **Date**: 2026-07
- **Related**: [#712](https://github.com/lfnovo/open-notebook/issues/712) (multi-user umbrella),
  [VISION.md](../../../VISION.md) (Current Posture)

## Context

Multi-user support is a recurring community request (#712 tracks it), and it would be a deep
platform redesign: auth, data scoping, permissions, and what "multi-user" even means for a
privacy-first self-hosted tool (household/team vs. SaaS-style). That strategic call hasn't been
made. Meanwhile, features keep shipping — and each one can silently bake in single-tenancy
assumptions that make the future redesign more expensive.

## Decision

Open Notebook remains a **single-user product for now** — but this is a *directional constraint*,
not a verdict: **new features must not gratuitously preclude multi-user.** Concretely, when
designing a feature, avoid hard-coding single-tenancy where a neutral choice costs the same:
data models that could carry an owner scope, auth touchpoints that assume exactly one identity,
global singletons for per-user state.

This record does **not** commit to building multi-user. It commits to keeping the door open until
the vision call in #712 is made.

## Alternatives considered

- **Decide multi-user now** — premature: the product core is still stabilizing (see Current
  Posture in VISION.md) and the design space (team vs. SaaS) is unresolved.
- **Ignore it until decided** — cheapest today, but every single-tenant assumption shipped
  becomes migration debt.

## Consequences

- Card design/triage gains a concrete check: "does this preclude multi-user?"
- Slight design overhead on data-model and auth decisions.
- When the #712 vision call is made, a new PDR supersedes or extends this one.
