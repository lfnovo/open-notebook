import '@testing-library/jest-dom'
import { afterEach } from 'vitest'
import { cleanup } from '@testing-library/react'

// Clean up the DOM after each test to avoid test pollution
afterEach(() => {
  cleanup()
})

// Polyfills that some components rely on
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false,
  }),
})

class MockIntersectionObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
  takeRecords() { return [] }
}

// Assign to globalThis with generic typing
;(globalThis as Record<string, unknown>).IntersectionObserver = MockIntersectionObserver as unknown

class MockResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
}

;(globalThis as Record<string, unknown>).ResizeObserver = MockResizeObserver as unknown
