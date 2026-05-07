import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import type { ComponentType, ReactNode } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { PublicNotebooks } from './PublicNotebooks'

const { listPublic } = vi.hoisted(() => ({
  listPublic: vi.fn(),
}))

vi.mock('@/lib/api/notebooks', () => ({
  notebooksApi: {
    listPublic,
  },
}))

function renderWithQueryClient(ui: ReactNode) {
  const client = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  })

  return render(
    <QueryClientProvider client={client}>
      {ui}
    </QueryClientProvider>
  )
}

describe('PublicNotebooks', () => {
  beforeEach(() => {
    listPublic.mockReset()
    listPublic.mockResolvedValue([
      {
        id: 'notebook:public',
        name: '公开测试笔记本',
        description: 'A public notebook',
        archived: false,
        created: '2026-05-01T00:00:00Z',
        updated: '2026-05-01T00:00:00Z',
        source_count: 1,
        note_count: 3,
        view_count: 18,
        reference_count: 4,
        password: null,
        creator_name: null,
        creator_username: 'owner',
        owner_id: 'app_user:owner',
        workspace_id: 'workspace:public',
        visibility: 'public',
        capabilities: {
          can_read: true,
          can_update: false,
          can_delete: false,
          can_share: false,
          can_create_source: false,
          can_create_note: false,
          can_create_chat: false,
          member_can_delete_source: false,
          member_can_delete_note: false,
          member_can_delete_chat: false,
          role: 'viewer',
          reason: null,
        },
      },
    ])
  })

  it('requests the top 20 public notebooks by visits and renders metrics', async () => {
    const Component = PublicNotebooks as unknown as ComponentType<{
      searchQuery?: string
      rankingMode: 'most_visited'
    }>

    renderWithQueryClient(<Component rankingMode="most_visited" />)

    await waitFor(() => {
      expect(listPublic).toHaveBeenCalledWith({
        order_by: 'view_count desc',
        limit: 20,
        offset: 0,
      })
    })
    expect(await screen.findByText('公开测试笔记本')).toBeInTheDocument()
    expect(screen.getByText('Created by owner')).toBeInTheDocument()
    expect(screen.getByText('18 views')).toBeInTheDocument()
    expect(screen.getByText('4 references')).toBeInTheDocument()
  })
})
