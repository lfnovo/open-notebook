import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { renderHook, waitFor } from '@testing-library/react'
import { ReactNode, createElement } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { sourcesApi } from '@/lib/api/sources'
import { useNotebookSources } from './use-sources'

let currentWorkspaceId: string | null = 'workspace:personal'

vi.mock('@/lib/api/sources', () => ({
  sourcesApi: {
    list: vi.fn(),
  },
}))

vi.mock('@/lib/stores/workspace-store', () => ({
  useWorkspaceStore: vi.fn((selector: (state: { currentWorkspaceId: string | null }) => unknown) =>
    selector({ currentWorkspaceId })
  ),
}))

function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
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

describe('useNotebookSources', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    currentWorkspaceId = 'workspace:personal'
    vi.mocked(sourcesApi.list).mockResolvedValue([])
  })

  it('does not filter notebook detail sources by the current workspace', async () => {
    const wrapper = createWrapper(createTestQueryClient())

    renderHook(() => useNotebookSources('notebook:public'), { wrapper })

    await waitFor(() => expect(sourcesApi.list).toHaveBeenCalled())

    expect(sourcesApi.list).toHaveBeenCalledWith({
      notebook_id: 'notebook:public',
      limit: 30,
      offset: 0,
      sort_by: 'updated',
      sort_order: 'desc',
    })
  })
})
