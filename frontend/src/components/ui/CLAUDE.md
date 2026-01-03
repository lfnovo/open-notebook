# UI Components Module

Radix UI-based accessible component library with CVA styling, composed building blocks, and theming support.

## Key Components

- **Primitives** (`button.tsx`, `dialog.tsx`, `select.tsx`, `dropdown-menu.tsx`): Radix UI wrappers with Tailwind styling
- **Composite components** (`checkbox-list.tsx`, `wizard-container.tsx`, `command.tsx`): Multi-part patterns combining primitives
- **Form components** (`input.tsx`, `textarea.tsx`, `label.tsx`, `form-section.tsx`): Input handling with accessibility
- **Feedback** (`alert.tsx`, `alert-dialog.tsx`, `sonner.tsx`, `progress.tsx`): User notifications and status
- **Layout** (`card.tsx`, `accordion.tsx`, `tabs.tsx`, `scroll-area.tsx`): Structural wrappers
- **Utilities** (`badge.tsx`, `separator.tsx`, `tooltip.tsx`, `popover.tsx`, `collapsible.tsx`): Small focused components

## Important Patterns

- **Radix UI wrappers**: Components delegate to Radix primitives; apply Tailwind classes via `cn()` utility
- **CVA (Class Variance Authority)**: `button.tsx` and similar use CVA for variant/size combinations
- **Composition via Slot**: `Button` uses `asChild` prop + `Slot` from radix to render as any element type
- **Data slots**: All components have `data-slot` attributes for testing/styling isolation
- **Controlled styling**: Classes hardcoded in components; use `className` prop to override/extend
- **Animations**: Radix `data-[state]` selectors for open/close animations (fade-in, zoom-in)
- **Accessibility first**: ARIA attributes from Radix (aria-invalid, sr-only labels, focus rings)
- **Dark mode support**: Uses Tailwind dark: prefix for color scheme (e.g., `dark:border-input`)

## Key Dependencies

- `@radix-ui/*`: Unstyled accessible primitives (dialog, select, dropdown-menu, etc.)
- `class-variance-authority`: CVA for variant patterns
- `lucide-react`: Icon library (XIcon in dialog close button)
- `@/lib/utils`: `cn()` utility for class merging

## How to Add New Components

1. Create `.tsx` file wrapping Radix primitive or composing existing components
2. Add `data-slot="component-name"` to root element
3. Use `cn()` to merge default classes with `className` prop
4. Export both component and variants (if using CVA)
5. Document prop shape and usage in JSDoc

## Important Quirks & Gotchas

- **Slot forwarding**: `asChild={true}` on Button passes all props to child; ensure child accepts them
- **FormData in dialogs**: Dialog not reset automatically; parent must manually clear form state
- **Focus management**: Dialog auto-focuses first input; can cause layout shifts if inputs conditionally rendered
- **Z-index stacking**: Fixed elements (Dialog overlay, dropdown menus) use z-50; be careful with other fixed elements
- **Click outside closes dropdown**: Radix dropdowns auto-close on outside click; may conflict with hover-triggered actions
- **SVG size inference**: Button uses `[&_svg:not([class*='size-'])]:size-4` to default unlabeled icons to 4x4; be explicit if different size needed
- **CSS-in-JS conflicts**: Hardcoded Tailwind classes may conflict with global CSS; specificity matters
- **Dark mode class**: Requires `dark` class on document root; not automatic with prefers-color-scheme alone

## Testing Patterns

```typescript
// Test component rendering with props
render(<Button variant="destructive" size="sm">Delete</Button>)
expect(screen.getByRole('button')).toHaveClass('bg-destructive')

// Test Dialog interaction
render(<Dialog open={true}><DialogContent>Content</DialogContent></Dialog>)
expect(screen.getByText('Content')).toBeInTheDocument()

// Test accessibility
expect(screen.getByRole('dialog')).toHaveAttribute('role', 'dialog')
```
