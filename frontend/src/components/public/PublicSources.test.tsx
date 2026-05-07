import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import type { ComponentType, ReactNode } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { PublicSources } from './PublicSources'

const { listPublic } = vi.hoisted(() => ({
  listPublic: vi.fn(),
}))

vi.mock('@/lib/api/sources', () => ({
  sourcesApi: {
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

describe('PublicSources', () => {
  beforeEach(() => {
    listPublic.mockReset()
    listPublic.mockResolvedValue([
      {
        id: 'source:public',
        title: 'BSD handbook',
        topics: [],
        asset: null,
        embedded: true,
        embedded_chunks: 4,
        kg_extracted: false,
        insights_count: 2,
        reference_count: 6,
        view_count: 12,
        created: '2026-05-01T00:00:00Z',
        updated: '2026-05-01T00:00:00Z',
        owner_id: 'app_user:owner',
        creator_username: 'source-owner',
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

  it('requests the top 20 public sources by reference count and renders metrics', async () => {
    const Component = PublicSources as unknown as ComponentType<{
      searchQuery?: string
      rankingMode: 'most_referenced'
    }>

    renderWithQueryClient(<Component rankingMode="most_referenced" />)

    await waitFor(() => {
      expect(listPublic).toHaveBeenCalledWith({
        sort_by: 'reference_count',
        sort_order: 'desc',
        limit: 20,
        offset: 0,
      })
    })
    expect(await screen.findByText('BSD handbook')).toBeInTheDocument()
    expect(screen.getByText('Created by source-owner')).toBeInTheDocument()
    expect(screen.getByText('12 views')).toBeInTheDocument()
    expect(screen.getByText('6 references')).toBeInTheDocument()
  })
})
