# Frontend Rules (frontend/)

Normative rules for working on the Next.js frontend. Architecture and flow walkthroughs live in
[docs/7-DEVELOPMENT/frontend.md](../docs/7-DEVELOPMENT/frontend.md) — this file is only what you
must know before changing code. Project-wide rules are in the root [AGENTS.md](../AGENTS.md).

## Commands (run inside `frontend/`)

- Dev server: `npm run dev` (port 3000; API must be up at 5055 first)
- Lint: `npm run lint` (`eslint src/`)
- Tests: `npm run test` (`vitest run`) · coverage: `npm run test:coverage`
- Build: `npm run build`

## Hard rules

- **i18n is mandatory**: every UI string goes through `t('section.key')` and the key must exist in
  **all 7 locales** (`en-US`, `pt-BR`, `zh-CN`, `zh-TW`, `ja-JP`, `ru-RU`, `bn-IN`) under
  `src/lib/locales/`. Missing keys fall back to en-US silently — keep locales in sync.
- All requests go through `apiClient` (`src/lib/api/client.ts`); never create a second axios
  instance. Auth token is auto-added from localStorage key `auth-storage`.
- Data fetching uses TanStack Query hooks in `src/lib/hooks/` with `QUERY_KEYS`; mutations
  invalidate caches and show toasts (sonner). Follow the existing hook shape.
- FormData requests: nested objects/arrays must be `JSON.stringify`-ed before appending; the
  interceptor strips Content-Type so the browser sets the multipart boundary — don't re-add it.
- No automatic request retry — handle failures in the consuming code (podcast retry is an explicit
  endpoint/hook, not a client retry).

## Gotchas

- Zustand stores with `persist`: check `hasHydrated` before rendering persisted state (SSR
  hydration mismatch), and keep each store's `name` key unique (localStorage collision).
- `NEXT_PUBLIC_API_TIMEOUT_MS`: default 600000 (10 min) for slow LLM calls; `0` disables the timeout.
- SSE (`useAsk`): incomplete lines stay in the buffer between reads; incomplete JSON is silently
  skipped — don't "simplify" the buffer handling.
- `useSourceStatus` polls every 2s while status is `running`/`queued`/`new`.
- Cache invalidation is deliberately broad (e.g. `['sources']` hits all source queries) — a
  simplicity/perf trade-off, be precise only when it matters.
- Dark mode requires the `dark` class on the document root (next-themes), not just
  `prefers-color-scheme`.
- Dialogs don't auto-reset form state (parent clears it) and auto-focus the first input (layout
  shift risk with conditional inputs). Fixed overlays use `z-50`.
- Provider nesting order in `app/layout.tsx` matters: ErrorBoundary → ThemeProvider →
  QueryProvider → I18nProvider → ConnectionGuard → Toaster. ErrorBoundary is a class component and
  uses the raw `enUS` locale object (no hooks).
- `i18n` runs with `useSuspense: false` (no SSR for translations).

## Deep dives

[frontend architecture](../docs/7-DEVELOPMENT/frontend.md) ·
[credentials system](../docs/7-DEVELOPMENT/credentials.md) ·
[change playbooks](../docs/7-DEVELOPMENT/change-playbooks.md) (i18n / frontend-only changes) ·
[code standards](../docs/7-DEVELOPMENT/code-standards.md)
