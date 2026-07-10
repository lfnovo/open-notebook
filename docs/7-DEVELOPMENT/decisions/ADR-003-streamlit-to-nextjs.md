# ADR-003: Migrate the UI from Streamlit to Next.js

- **Status**: Accepted
- **Date**: 2026-07 (retroactive record — migration shipped with the v1→v2 platform rework)
- **Related**: [frontend.md](../frontend.md), API-first principle in [VISION.md](../../../VISION.md)

## Context

The original UI was Streamlit: fast to build, but it coupled UI and backend logic in one process,
made external integrations hard, and gave us limited control over API behavior. The API-first
principle — every capability accessible via REST, the UI being just one client — was structurally
impossible to honor.

## Decision

Rebuild the frontend as a **Next.js/React application** consuming the same FastAPI REST API that
external clients use. Business logic lives behind the API; the frontend is a pure client
(TanStack Query + Zustand over axios).

## Alternatives considered

- **Stay on Streamlit** — lowest effort, but permanently blocks API-first and a polished UX.
- **Server-rendered templates (FastAPI + Jinja)** — simpler stack, but poor interactivity for
  chat/streaming-heavy UX.
- **Other SPA frameworks (Vue, Svelte)** — viable; React/Next.js won on ecosystem, component
  library availability (Radix/Shadcn) and contributor familiarity.

## Consequences

- The API is complete by construction — anything the UI does, an integration can do (this later
  enabled the MCP direction, #878).
- Two build systems and a larger contributor surface (TypeScript + Python).
- i18n, theming and accessibility became first-class frontend concerns (7 locales today).
- Legacy Streamlit remnants were removed over time; migrations assume API-driven access.
