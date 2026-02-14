import '@testing-library/jest-dom'
import { vi } from 'vitest'
import { enUS } from '../lib/locales/en-US'

// Mock next/navigation
vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
    prefetch: vi.fn(),
  }),
  usePathname: () => '',
  useSearchParams: () => new URLSearchParams(),
}))

// Mock window.matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(), // Deprecated
    removeListener: vi.fn(), // Deprecated
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
})

// Mock @/lib/hooks/use-translation with full locale structure
vi.mock('../lib/hooks/use-translation', () => {
  // Create a mock that supports both t('key') and t.key access patterns
  // This mimics the Proxy-based behavior of the real useTranslation hook
  const makeT = () => {
    // Simple approach: use the real enUS locale with nested object access
    const t: any = (key?: string) => {
      if (typeof key === 'string') {
        // Split key by '.' and traverse enUS
        const parts = key.split('.')
        let value: any = enUS
        for (const part of parts) {
          if (value && typeof value === 'object' && part in value) {
            value = value[part]
          } else {
            // Key not found, return the key itself (i18n behavior)
            return key
          }
        }
        return value
      }
      return enUS
    }

    // Create proxy for nested property access (t.common.clickToEdit)
    return new Proxy(t, {
      get: (target: any, prop: string | symbol) => {
        if (typeof prop !== 'string') return undefined
        // Try to get from enUS using the prop as a key path
        const parts = prop.split('.')
        let value: any = enUS
        for (const part of parts) {
          if (value && typeof value === 'object' && part in value) {
            value = value[part]
          } else {
            // Key not found, return the prop itself (for any() matcher to work)
            return prop
          }
        }
        return value
      },
    })
  }

  return {
    useTranslation: () => ({
      t: makeT(),
      language: 'en-US',
      setLanguage: vi.fn(),
    }),
  }
})

// Mock @/lib/hooks/use-auth
vi.mock('@/lib/hooks/use-auth', () => ({
  useAuth: vi.fn(() => ({
    user: { id: '1', email: 'test@example.com' },
    logout: vi.fn(),
    isLoading: false,
  })),
}))

// Mock @/lib/stores/sidebar-store
vi.mock('@/lib/stores/sidebar-store', () => ({
  useSidebarStore: vi.fn(() => ({
    isCollapsed: false,
    toggleCollapse: vi.fn(),
  })),
}))

// Mock @/lib/hooks/use-create-dialogs
vi.mock('@/lib/hooks/use-create-dialogs', () => ({
  useCreateDialogs: vi.fn(() => ({
    openSourceDialog: vi.fn(),
    openNotebookDialog: vi.fn(),
    openPodcastDialog: vi.fn(),
  })),
}))
