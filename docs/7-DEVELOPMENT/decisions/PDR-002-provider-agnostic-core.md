# PDR-002: Provider-agnostic core by default; provider-exclusive capabilities require a PDR

- **Status**: Accepted
- **Date**: 2026-07
- **Related**: [ADR-002](ADR-002-esperanto-multi-provider.md), [VISION.md](../../../VISION.md)
  (Principles + Current Posture)

## Context

Our philosophy is to support as many providers as makes sense — users choose their AI, including
fully local. The cost of that democratic stance is that we don't immediately adopt capabilities
unique to one provider, even compelling ones. But "portable by default" must not harden into
"never": some provider-exclusive capabilities (including paid-only ones) may be worth adopting
deliberately. The current phase (see VISION.md posture) is basics-first; that phase is expected
to evolve — the decision is to evolve, not to stand still.

## Decision

Two rules with different lifespans:

1. **Durable principle**: the core is provider-agnostic. Features must work across the provider
   matrix by default. Adopting a provider-exclusive capability is *allowed*, but it is a
   deliberate product decision that requires its own PDR (stating scope, fallback behavior for
   other providers, and why the exclusivity is worth it).
2. **Current posture** (temporal, lives in VISION.md): in the basics-first phase, we lean
   portable. Expanding into provider-exclusive premium capabilities is a phase change, recorded
   as a short PDR when it happens — that will be the principle working, not a reversal.

## Alternatives considered

- **Hard rule: never provider-exclusive** — protects portability but forfeits real capabilities
  and doesn't reflect our actual intent.
- **No rule: adopt case-by-case silently** — drifts into de-facto lock-in one convenient feature
  at a time.

## Consequences

- Triage/design gets a crisp test: "does this only work on provider X?" → needs a PDR, not just
  an implementation.
- Feature requests for provider-exclusive capabilities aren't auto-rejected — they're routed to a
  deliberate decision.
- Slower adoption of shiny provider features, by design, during the basics-first phase.
