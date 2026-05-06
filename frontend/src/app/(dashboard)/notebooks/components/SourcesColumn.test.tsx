import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { SourceListResponse } from '@/lib/types/api'
import { SourcesColumn } from './SourcesColumn'

vi.mock('@/lib/hooks/use-profile', () => ({
  useProfile: vi.fn(() => ({
    data: { id: 'app_user:owner', username: 'owner' },
  })),
}))

vi.mock('@/lib/hooks/use-modal-manager', () => ({
  useModalManager: () => ({
    openModal: vi.fn(),
  }),
}))

vi.mock('@/lib/hooks/use-sources', () => ({
  useDeleteSource: () => ({
    mutateAsync: vi.fn(),
    isPending: false,
  }),
  useRetrySource: () => ({
    mutateAsync: vi.fn(),
  }),
  useRemoveSourceFromNotebook: () => ({
    mutateAsync: vi.fn(),
    isPending: false,
  }),
}))

vi.mock('@/components/notebooks/CollapsibleColumn', () => ({
  CollapsibleColumn: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  createCollapseButton: () => null,
}))

vi.mock('@/components/sources/AddSourceDialog', () => ({
  AddSourceDialog: () => null,
}))

vi.mock('@/components/sources/AddExistingSourceDialog', () => ({
  AddExistingSourceDialog: () => null,
}))

vi.mock('@/components/common/ConfirmDialog', () => ({
  ConfirmDialog: () => null,
}))

vi.mock('@/components/sources/SourceCard', () => ({
  SourceCard: ({
    source,
    onDelete,
    onRemoveFromNotebook,
  }: {
    source: SourceListResponse
    onDelete?: (sourceId: string) => void
    onRemoveFromNotebook?: (sourceId: string) => void
  }) => (
    <div
      data-testid={`source-card-${source.id}`}
      data-delete-enabled={onDelete ? 'true' : 'false'}
      data-remove-enabled={onRemoveFromNotebook ? 'true' : 'false'}
    >
      {source.title}
    </div>
  ),
}))

const source = (overrides: Partial<SourceListResponse>): SourceListResponse => ({
  id: 'source:base',
  title: 'Base',
  topics: [],
  asset: null,
  embedded: true,
  embedded_chunks: 1,
  kg_extracted: false,
  insights_count: 0,
  reference_count: 0,
  created: '2026-05-05T00:00:00Z',
  updated: '2026-05-05T00:00:00Z',
  owner_id: 'app_user:owner',
  visibility: 'private',
  ...overrides,
})

describe('SourcesColumn', () => {
  it('only enables source deletion for deletable notebook sources', () => {
    render(
      <SourcesColumn
        sources={[
          source({ id: 'source:owned', title: 'Owned' }),
          source({ id: 'source:other', title: 'Other', owner_id: 'app_user:other' }),
        ]}
        isLoading={false}
        notebookId="notebook:one"
      />
    )

    expect(screen.getByTestId('source-card-source:owned')).toHaveAttribute(
      'data-delete-enabled',
      'true'
    )
    expect(screen.getByTestId('source-card-source:other')).toHaveAttribute(
      'data-delete-enabled',
      'false'
    )
  })

  it('disables source removal and deletion when the notebook cannot be managed', () => {
    render(
      <SourcesColumn
        sources={[
          source({
            id: 'source:owned',
            title: 'Owned',
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
          }),
        ]}
        isLoading={false}
        notebookId="notebook:team-owned"
        canManageNotebook={false}
      />
    )

    expect(screen.getByTestId('source-card-source:owned')).toHaveAttribute(
      'data-delete-enabled',
      'false'
    )
    expect(screen.getByTestId('source-card-source:owned')).toHaveAttribute(
      'data-remove-enabled',
      'false'
    )
  })

  it('allows adding sources while keeping remove disabled when capabilities split those actions', () => {
    render(
      <SourcesColumn
        sources={[source({ id: 'source:owned', title: 'Owned' })]}
        isLoading={false}
        notebookId="notebook:team"
        canManageNotebook={false}
        canCreateSource={true}
        canRemoveSource={false}
      />
    )

    expect(screen.getByRole('button', { name: /Add Source/i })).not.toBeDisabled()
    expect(screen.getByTestId('source-card-source:owned')).toHaveAttribute(
      'data-remove-enabled',
      'false'
    )
  })
})
