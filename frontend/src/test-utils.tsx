import React, { ReactElement } from 'react'
import { render, RenderOptions, RenderResult } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import userEvent from '@testing-library/user-event'

/**
 * Custom render function that wraps components with necessary providers
 * This ensures all tests have access to React Query, themes, etc.
 */

interface CustomRenderOptions extends Omit<RenderOptions, 'wrapper'> {
  queryClient?: QueryClient
}

interface CustomRenderResult extends RenderResult {
  user: ReturnType<typeof userEvent.setup>
}

/**
 * Creates a new QueryClient instance with default test configuration
 * Disables retries and sets short cache times for faster tests
 */
export function createTestQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false, // Don't retry failed queries in tests
        gcTime: 0, // Disable garbage collection
        staleTime: 0, // Data is always considered stale
      },
      mutations: {
        retry: false, // Don't retry failed mutations in tests
      },
    },
  })
}

/**
 * Custom render that includes all necessary providers
 */
export function renderWithProviders(
  ui: ReactElement,
  {
    queryClient = createTestQueryClient(),
    ...renderOptions
  }: CustomRenderOptions = {}
): CustomRenderResult {
  function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        {children}
      </QueryClientProvider>
    )
  }

  const user = userEvent.setup()

  return {
    ...render(ui, { wrapper: Wrapper, ...renderOptions }),
    user,
  }
}

/**
 * Re-export everything from React Testing Library
 * This allows tests to import everything from this single file
 */
export * from '@testing-library/react'
export { userEvent }

/**
 * Custom matchers and utilities
 */

/**
 * Wait for a specific amount of time (useful for debounced inputs)
 */
export const waitFor = (ms: number): Promise<void> => 
  new Promise(resolve => setTimeout(resolve, ms))

/**
 * Mock localStorage for tests
 */
export const mockLocalStorage = (() => {
  let store: Record<string, string> = {}

  return {
    getItem: (key: string) => store[key] || null,
    setItem: (key: string, value: string) => {
      store[key] = value.toString()
    },
    removeItem: (key: string) => {
      delete store[key]
    },
    clear: () => {
      store = {}
    },
    get length() {
      return Object.keys(store).length
    },
    key: (index: number) => Object.keys(store)[index] || null,
  }
})()

/**
 * Setup and teardown for localStorage mock
 */
export function setupLocalStorageMock() {
  beforeEach(() => {
    Object.defineProperty(window, 'localStorage', {
      value: mockLocalStorage,
      writable: true,
    })
    mockLocalStorage.clear()
  })

  afterEach(() => {
    mockLocalStorage.clear()
  })
}

/**
 * Helper to mock successful API responses
 */
export function createMockSuccessResponse<T>(data: T) {
  return Promise.resolve({ 
    data, 
    status: 200, 
    statusText: 'OK', 
    headers: {}, 
    config: {} as Record<string, unknown>
  })
}

/**
 * Helper to mock API errors
 */
export function createMockErrorResponse(status: number, message: string) {
  return Promise.reject({
    response: {
      status,
      data: { message },
      statusText: 'Error',
      headers: {},
      config: {} as Record<string, unknown>,
    },
  })
}

/**
 * Wait for React Query to finish all pending operations
 */
export async function waitForQueryClient(queryClient: QueryClient) {
  await queryClient.cancelQueries()
  await new Promise(resolve => setTimeout(resolve, 0))
}
