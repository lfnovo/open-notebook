# ADR-009: RTL Layout & Internationalization Architecture

- **Status**: Accepted
- **Date**: 2026-09-25

## Context
With the introduction of Arabic (`ar-YE`) as a supported localization in Open Notebook, the frontend architecture required a holistic upgrade to natively support Right-to-Left (RTL) reading directions. Supporting RTL dynamically without requiring hard page reloads or duplicating CSS layouts requires strict adherence to logical layout principles across Tailwind CSS, Radix UI primitives, React state, and iconography.

During the initial implementation, the following architectural challenges were identified:
1. **Physical Layout Hardcoding**: Historic UI components relied heavily on physical CSS coordinates (`ml-`, `pr-`, `left-0`, `border-l`), which lock layouts into a Left-to-Right structure.
2. **Disconnected Direction State**: The `DirectionProvider` managed `document.documentElement.dir` purely as a DOM side effect. React components reading this DOM attribute directly during their render phase received stale state when the user swapped languages, causing layout breakage (e.g., tooltips anchoring to the wrong side) until a full page reload.
3. **Missing Radix UI Context**: The app relies heavily on Radix UI (`DropdownMenu`, `Select`, `ScrollArea`, `Tabs`). Without explicit context, Radix defaults internal keyboard navigation and placement logic to LTR, meaning arrow keys were functionally backward for RTL users, and scrollbars overlapped text.
4. **Hardcoded Icon Directionality**: Semantic icons like `Send` (pointing right for progression) and `AlignLeft` (for text sources) were physically locked, contradicting RTL alignment.

## Decision

To establish a robust, maintainable RTL-aware architecture, we have adopted the following structural standards:

1. **Logical Tailwind Properties**: All physical Tailwind utility classes (e.g., `ml-*`, `pr-*`, `left-*`) have been systematically replaced with their logical equivalents (e.g., `ms-*`, `pe-*`, `inset-inline-start-*`). The frontend must exclusively use logical properties for all margins, padding, borders, and positioning.
2. **Global Radix Direction Provider**: We introduced `@radix-ui/react-direction` and wrapped the main application tree inside `DirectionProvider.tsx`. All Radix primitives automatically inherit the correct text direction. This correctly mirrors dropdown sub-menus, popup placements, and reverses keyboard arrow navigation for RTL.
3. **Reactive Direction Hook (`useDirection`)**: Any React component that needs to dynamically adapt to the text direction must use the `useDirection()` hook (which subscribes to `I18N_LANGUAGE_CHANGE_END` and DOM mutations) rather than synchronously reading `document.documentElement.dir`. This guarantees safe React hydration and re-rendering on language swap.
4. **Semantic Directional Icons**: Icons that convey progression or text alignment are managed via `directional-icons.tsx`. 
   - Uses `ChevronStart`/`End` and `ArrowStart`/`End` for navigation.
   - Uses `AlignStart` (swapping between `AlignLeft` and `AlignRight`) for text alignment representation.
   - Uses `SendDirectional` (mirroring the `Send` icon for RTL) to correctly reflect visual progression semantics.
5. **Editor Direction Awareness**: Third-party components like `MarkdownEditor` (`@uiw/react-md-editor`) are explicitly wrapped in DOM nodes carrying `dir={dir}` derived from `useDirection()` to ensure their internal flex layouts (e.g., side-by-side split panes) and CodeMirror cursors receive explicit bidirectional hinting.

## Alternatives considered

- **Duplicate Layouts**: Maintaining separate LTR and RTL component trees. Rejected due to maintenance overhead and drift.
- **Page Reload on Language Swap**: Forcing a hard reload to apply `dir="rtl"` to `<html>`. Rejected because it breaks SPA experience and disrupts active chat sessions.

## Consequences
- **Positive:** Open Notebook now supports fluid, dynamic switching between LTR and RTL languages (like Arabic) without a page reload.
- **Positive:** Keyboard accessibility and structural layouts are fully correct for RTL users out-of-the-box.
- **Positive:** The codebase is cleaner and relies entirely on modern CSS logical properties.
- **Negative:** When introducing new third-party libraries or Radix UI primitives, developers must actively ensure they don't explicitly pass physical configurations that override the inherited directional context.
