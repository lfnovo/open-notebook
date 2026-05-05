import { render, screen, waitFor, within } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { SourceDetailContent } from './SourceDetailContent'

vi.mock('@tanstack/react-query', () => ({
  useQueryClient: () => ({
    invalidateQueries: vi.fn(),
  }),
}))

vi.mock('@/lib/hooks/use-profile', () => ({
  useProfile: vi.fn(() => ({
    data: { id: 'app_user:viewer', username: 'viewer' },
  })),
}))

vi.mock('@/lib/api/sources', () => ({
  sourcesApi: {
    get: vi.fn(async () => ({
      id: 'source:shared',
      title: 'Shared Source',
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
      visibility: 'team',
      full_text: 'content',
      notebooks: [],
    })),
    update: vi.fn(),
    delete: vi.fn(),
    downloadFile: vi.fn(),
  },
}))

vi.mock('@/lib/api/insights', () => ({
  insightsApi: {
    listForSource: vi.fn(async () => []),
    create: vi.fn(),
    delete: vi.fn(),
    waitForCommand: vi.fn(),
  },
}))

vi.mock('@/lib/api/transformations', () => ({
  transformationsApi: {
    list: vi.fn(async () => []),
  },
}))

vi.mock('@/lib/api/embedding', () => ({
  embeddingApi: {
    embedContent: vi.fn(),
  },
}))

vi.mock('@/components/source/NotebookAssociations', () => ({
  NotebookAssociations: () => null,
}))

vi.mock('@/components/source/SourceInsightDialog', () => ({
  SourceInsightDialog: () => null,
}))

vi.mock('@/components/ui/dropdown-menu', () => ({
  DropdownMenu: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  DropdownMenuTrigger: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="source-actions-trigger">{children}</div>
  ),
  DropdownMenuContent: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  DropdownMenuItem: ({
    children,
    disabled,
  }: {
    children: React.ReactNode
    disabled?: boolean
  }) => (
    <button type="button" disabled={disabled}>
      {children}
    </button>
  ),
  DropdownMenuSeparator: () => <hr />,
}))

describe('SourceDetailContent', () => {
  it('disables the source actions menu for read-only sources', async () => {
    render(<SourceDetailContent sourceId="source:shared" />)

    await waitFor(() => expect(screen.getByText('Shared Source')).toBeInTheDocument())

    const trigger = screen.getByTestId('source-actions-trigger')
    expect(within(trigger).getByRole('button')).toBeDisabled()
  })
})
