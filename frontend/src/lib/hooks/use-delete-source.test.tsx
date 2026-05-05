import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, renderHook, waitFor } from '@testing-library/react'
import { ReactNode, createElement } from 'react'
import { describe, expect, it, vi } from 'vitest'
import { sourcesApi } from '@/lib/api/sources'
import { useDeleteSource } from './use-sources'

vi.mock('@/lib/api/sources', () => ({
  sourcesApi: {
    delete: vi.fn(),
  },
}))

vi.mock('@/lib/hooks/use-toast', () => ({
  useToast: () => ({
    toast: vi.fn(),
  }),
}))

vi.mock('@/lib/hooks/use-translation', () => ({
  useTranslation: () => ({
    t: {
      common: {
        success: 'Success',
        error: 'Error',
      },
      sources: {
        sourceDeletedSuccess: 'Source deleted',
        failedToDeleteSource: 'Failed to delete source',
      },
    },
  }),
}))

function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
      mutations: {
        retry: false,
      },
    },
  })
}

function createWrapper(queryClient: QueryClient) {
  return function Wrapper({ children }: { children: ReactNode }) {
    return createElement(QueryClientProvider, { client: queryClient }, children)
  }
}

describe('useDeleteSource', () => {
  it('does not invalidate deleted source status queries after deletion succeeds', async () => {
    const queryClient = createTestQueryClient()
    const invalidateQueries = vi.spyOn(queryClient, 'invalidateQueries')
    const removeQueries = vi.spyOn(queryClient, 'removeQueries')
    const wrapper = createWrapper(queryClient)

    vi.mocked(sourcesApi.delete).mockResolvedValueOnce(undefined)

    const { result } = renderHook(() => useDeleteSource(), { wrapper })

    await act(async () => {
      await result.current.mutateAsync('source:deleted')
    })

    await waitFor(() => expect(sourcesApi.delete).toHaveBeenCalledWith('source:deleted'))
    expect(invalidateQueries).not.toHaveBeenCalledWith(
      expect.objectContaining({ queryKey: ['sources'] })
    )
    expect(removeQueries).toHaveBeenCalledWith({
      queryKey: ['sources', 'source:deleted', 'status'],
    })
  })
})
