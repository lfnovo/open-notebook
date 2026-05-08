import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { renderHook, waitFor } from '@testing-library/react'
import { ReactNode, createElement } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { workspacesApi } from '@/lib/api/workspaces'
import { useCurrentWorkspace } from './use-workspaces'

let currentWorkspaceId: string | null = 'workspace:stale'
const setCurrentWorkspaceId = vi.fn((workspaceId: string | null) => {
  currentWorkspaceId = workspaceId
})

vi.mock('@/lib/api/workspaces', () => ({
  workspacesApi: {
    list: vi.fn(),
  },
}))

vi.mock('@/lib/stores/workspace-store', () => ({
  useWorkspaceStore: vi.fn((selector: (state: {
    currentWorkspaceId: string | null
    setCurrentWorkspaceId: (workspaceId: string | null) => void
  }) => unknown) =>
    selector({ currentWorkspaceId, setCurrentWorkspaceId })
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

describe('useCurrentWorkspace', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    currentWorkspaceId = 'workspace:stale'
    vi.mocked(workspacesApi.list).mockResolvedValue({
      items: [
        {
          id: 'workspace:team',
          name: 'Research Team',
          type: 'team',
          current_user_role: 'viewer',
          can_manage: false,
        },
      ],
    })
  })

  it('replaces a stale workspace id with the first visible workspace', async () => {
    const wrapper = createWrapper(createTestQueryClient())

    renderHook(() => useCurrentWorkspace(), { wrapper })

    await waitFor(() => {
      expect(setCurrentWorkspaceId).toHaveBeenCalledWith('workspace:team')
    })
  })
})
