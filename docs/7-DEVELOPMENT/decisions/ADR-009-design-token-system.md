# ADR-009: Visual identity is a token contract in globals.css, reviewed through /dev/design

- **Status**: Accepted
- **Date**: 2026-07
- **Related**: Discussion #1202 (community co-design), #1218 (foundation), #1220 (screen reskin), [frontend rules](../../7-DEVELOPMENT/frontend.md)

## Context

The 2026 redesign ("Quiet Green", co-designed with the community in Discussion #1202) replaced the stock shadcn theme with a product-specific visual identity. Before it, colors were scattered across components as raw Tailwind palette classes (`text-red-600`, `bg-amber-50`), each with hand-written `dark:` twins — visually inconsistent, semantically meaningless, and expensive to change. The redesign also pre-designed Stage-2 UX (citations, per-source context states, content-type identity) that needs colors with *meaning*, not decoration.

## Decision

**All visual identity lives as a layered custom-property token system in `frontend/src/app/globals.css`. Components consume semantic tokens only — raw palette classes are banned. `/dev/design` is the living reference.**

- **Layers**: raw palette (fern, sage, gold, teal, plum, mauve, slate, violet, clay) → semantic slots (surfaces, ink ramp, hairlines, action, danger, warn) → product vocabularies: content-type hues (`--type-*`), evidence/citation classes (`--cite-*`), context states (`--ctx-*`). The product vocabularies are canonized now even where nothing consumes them yet, so Stage-2 features and community PRs share one contract.
- **The laws** (enforced in review): fern acts · teal speaks (the AI/system voice) · red destroys, and only destroys · warn is clay, never an action hue · color never washes a reading surface · hairlines separate, popovers own the only real shadow · geometry is squared (4–6px) · mono is for data, not prose.
- **Dark mode** overrides only the raw layers on `.dark`; every alias re-resolves via `var()`. This works **only** because the `dark` class sits on the document root (`theme-store` behavior). CSS custom properties resolve where they are *declared*, so a nested `.dark` wrapper inherits already-resolved light values — never theme a subtree.
- **Values are hex**, kept 1:1 with the validated design spec (a pixel-diff re-application test against the design mockups reached 0.000% visible difference). Converting to oklch would reintroduce drift for zero benefit.
- **`/dev/design`** (dev-only route, 404 in production) renders every token and primitive in both themes. It is the acceptance reference for visual PRs and the regression detector: screen-level PRs must leave it byte-identical.

## Alternatives considered

- **Keep per-component palette classes** — rejected: the status quo that produced the inconsistency; every rebrand becomes a 38-file sweep (we did exactly one and never want another).
- **A theming library / CSS-in-JS tokens** — rejected: Tailwind v4 `@theme` already bridges custom properties to utilities; adding a runtime dependency contradicts the lean posture.
- **Full design-system tooling (Storybook, Figma library, published npm package)** — rejected as over-engineering for a single-app project; `/dev/design` gives the same review value at near-zero maintenance cost.
- **oklch values (shadcn convention)** — rejected: fidelity to the pixel-diff-validated spec wins over convention; the file documents this so nobody "fixes" it later.

## Consequences

- Contributors must use token utilities (`text-destructive`, `bg-warn-tint`, `text-type-video`…) — see the styling rule in [frontend/AGENTS.md](../../../frontend/AGENTS.md). A PR reintroducing `text-red-600` is a review reject.
- `slate` and `violet` are exposed to Tailwind as `slate-hue`/`violet-hue` to avoid colliding with Tailwind's built-in palettes.
- Rebrands and theme tweaks are token edits, verified in `/dev/design`, instead of app-wide sweeps.
- Stage-2 features consume `--cite-*`/`--ctx-*` without new color decisions; the vocabulary already exists.
