import { render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import SourcesPage from './page'
import { sourcesApi } from '@/lib/api/sources'
import { SourceListResponse } from '@/lib/types/api'

vi.mock('@/lib/api/sources', () => ({
  sourcesApi: {
    list: vi.fn(),
    listPublic: vi.fn(),
    bulkDelete: vi.fn(),
    extractKg: vi.fn(),
    delete: vi.fn(),
  },
}))

vi.mock('@/lib/stores/workspace-store', () => ({
  useWorkspaceStore: vi.fn((selector: (state: { currentWorkspaceId: string }) => unknown) =>
    selector({ currentWorkspaceId: 'workspace:team' })
  ),
}))

vi.mock('@/lib/hooks/use-profile', () => ({
  useProfile: vi.fn(() => ({
    data: { id: 'app_user:member', username: 'member' },
  })),
}))

vi.mock('@/components/share/ShareDialog', () => ({
  ShareDialog: () => null,
}))

const source = (overrides: Partial<SourceListResponse>): SourceListResponse => ({
  id: 'source:base',
  title: 'Base source',
  topics: [],
  asset: null,
  embedded: true,
  embedded_chunks: 1,
  kg_extracted: true,
  insights_count: 0,
  reference_count: 0,
  created: '2026-05-05T00:00:00Z',
  updated: '2026-05-05T00:00:00Z',
  owner_id: 'app_user:owner',
  workspace_id: 'workspace:team',
  visibility: 'private',
  capabilities: {
    can_read: true,
    can_update: false,
    can_delete: false,
    can_share: false,
    can_manage: false,
    can_create_source: false,
    can_remove_source: false,
    can_create_note: false,
    can_process: false,
  },
  ...overrides,
})

describe('SourcesPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(sourcesApi.list).mockResolvedValue([
      source({ id: 'source:team', title: 'Team source', workspace_id: 'workspace:team' }),
    ])
    vi.mocked(sourcesApi.listPublic).mockResolvedValue([
      source({
        id: 'source:public',
        title: 'Public source',
        workspace_id: 'workspace:personal',
        visibility: 'public',
      }),
      source({
        id: 'source:team-public',
        title: 'Team public source',
        workspace_id: 'workspace:team',
        visibility: 'public',
      }),
    ] as Awaited<ReturnType<typeof sourcesApi.listPublic>>)
  })

  it('loads current workspace sources and public sources as separate groups', async () => {
    render(<SourcesPage />)

    await waitFor(() =>
      expect(sourcesApi.list).toHaveBeenCalledWith(
        expect.objectContaining({ workspace_id: 'workspace:team' })
      )
    )
    expect(sourcesApi.listPublic).toHaveBeenCalledWith(
      expect.objectContaining({ limit: 30, offset: 0 })
    )

    expect(await screen.findByText('Team workspace sources')).toBeInTheDocument()
    expect(screen.getByText('Team source')).toBeInTheDocument()
    expect(screen.getByText('Public sources')).toBeInTheDocument()
    expect(screen.getByText('Public source')).toBeInTheDocument()
    expect(screen.queryByText('Team public source')).not.toBeInTheDocument()
  })
})
