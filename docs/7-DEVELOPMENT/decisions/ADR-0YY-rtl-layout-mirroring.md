# ADR-0YY: RTL layout mirroring, stacked on the language/direction plumbing

- **Status**: Accepted
- **Date**: 2026-10-03
- **Related**: PR #1367 (language/direction plumbing + ar-SA locale), Discussion #1338

## Context

PR #1367 establishes the language/direction plumbing — canonicalized language resolution, a pre-hydration bootstrap script, `html lang`/`dir`, a root Radix `DirectionProvider`, and the ar-SA locale — but deliberately leaves layout mirroring out of scope ("Direction-sensitive component positioning and mixed-language user content still require their own layout decisions").

Without mirroring, spacing, borders, progress bars, sidebar affordances, toasts and semantic icons stay physically LTR for Arabic users. An earlier standalone implementation of this layout work (feature PR by @Alfrahi) duplicated the provider/hook plumbing and added a separate ar-YE locale; following maintainer review, the layout work is re-stacked on top of #1367 instead of competing with it.

The original implementation surfaced these real constraints:

1. **Physical layout hardcoding** — historical components used physical Tailwind utilities (`ml-*`, `pr-*`, `border-l`, `text-left`), which lock layouts into LTR regardless of `dir`.
2. **Stale DOM reads** — React components reading `document.documentElement.dir` during render receive stale state across a language swap until a full reload.
3. **Third-party direction gaps** — Sonner toasts and `@radix-ui/react-progress` do not mirror automatically; `@uiw/react-md-editor` needs its native `direction` prop (provided by #1367's editor change).
4. **Semantic icon directionality** — progression/alignment icons (`Send`, `AlignLeft`, chevrons) have physical meaning that contradicts RTL reading order.

## Decision

1. **Logical Tailwind properties, exclusively.** All physical directional utilities are replaced with logical equivalents (`ms-`/`me-`, `ps-`/`pe-`, `border-s`/`border-e`, `text-start`/`text-end`, `start-`/`end-`). A repo-wide guard test (`frontend/src/lib/logical-classes.test.ts`) fails the build if physical directional classes — or the invalid `bs`/`be` tokens produced by an earlier regex sweep — reappear in class strings.
2. **Single direction source.** Direction comes only from the Radix `DirectionProvider` inside `I18nProvider` (#1367). JS consumers read it via `useDirection()` from `@radix-ui/react-direction` (re-exported through `components/ui/directional-icons.tsx` for a stable import path). No second provider, no DOM-attribute reads, no custom event subscriptions for direction.
3. **Directional icon vocabulary.** Progression and text-alignment icons go through `ChevronStart`/`ChevronEnd`, `ArrowStart`/`ArrowEnd`, `SendDirectional` (mirrored), and `AlignStart` in `directional-icons.tsx`.
4. **Component-level mirroring.** The app sidebar mirrors tooltip/dropdown placement in collapsed mode; `Progress` fills from the inline-start edge; Sonner receives the current `dir`. The markdown editor's direction is owned by #1367 (native `direction` prop).

## Alternatives considered

- **Independent RTL PR with its own direction provider and bootstrap script** (the pre-stacking approach): duplicates #1367's plumbing; its DOM-authored direction synced via passive effects/MutationObserver lags behind paint, and reading `i18n.language` instead of `resolvedLanguage` yields RTL direction over English fallback content for unregistered language variants. Rejected in favor of stacking.
- **Duplicate LTR/RTL component trees**: rejected, maintenance drift.
- **Hard page reload on language swap**: rejected, breaks SPA continuity (chat sessions etc.).
- **Bundling mixed-language content isolation** (`dir="auto"` per message/badge, `<bdi>` citation wrapping, forced-LTR URLs/code): deliberately deferred to a follow-up PR pending scope confirmation in Discussion #1338.

## Consequences

- **Positive:** RTL users get a fully mirrored layout and correct keyboard navigation/placement through the Radix context, without reloads.
- **Positive:** The guard test makes the logical-properties policy self-enforcing.
- **Negative / deferred:** mixed-language content isolation, toast position mirroring, and non-Latin font subsets remain open follow-ups. New components must use logical utilities and, where needed, the directional icon vocabulary.
