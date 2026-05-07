import { render, screen, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { NotebookResponse } from '@/lib/types/api'
import NotebooksPage from './page'

let currentWorkspaceType: 'personal' | 'team' = 'personal'
let activeNotebooks: NotebookResponse[] = []
let archivedNotebooks: NotebookResponse[] = []
let publicNotebooks: NotebookResponse[] = []

vi.mock('@/lib/hooks/use-notebooks', () => ({
  useNotebooks: vi.fn((archived?: boolean) => ({
    data: archived ? archivedNotebooks : activeNotebooks,
    isLoading: false,
    refetch: vi.fn(),
  })),
  usePublicNotebooks: vi.fn(() => ({
    data: publicNotebooks,
    isLoading: false,
    refetch: vi.fn(),
  })),
}))

vi.mock('@/lib/hooks/use-workspaces', () => ({
  useCurrentWorkspace: vi.fn(() => ({
    currentWorkspaceId: `workspace:${currentWorkspaceType}`,
    currentWorkspace: {
      id: `workspace:${currentWorkspaceType}`,
      name: currentWorkspaceType === 'personal' ? 'Personal' : 'Research Team',
      type: currentWorkspaceType,
    },
  })),
}))

vi.mock('@/components/notebooks/CreateNotebookDialog', () => ({
  CreateNotebookDialog: () => null,
}))

vi.mock('./components/NotebookList', () => ({
  NotebookList: ({
    title,
    notebooks,
  }: {
    title: string
    notebooks?: NotebookResponse[]
  }) => (
    <section aria-label={title}>
      <h2>{title}</h2>
      {(notebooks || []).map((notebook) => (
        <div key={notebook.id}>{notebook.name}</div>
      ))}
    </section>
  ),
}))

const notebook = (overrides: Partial<NotebookResponse>): NotebookResponse => ({
  id: 'notebook:base',
  name: 'Base notebook',
  description: '',
  archived: false,
  created: '2026-05-05T00:00:00Z',
  updated: '2026-05-05T00:00:00Z',
  source_count: 0,
  note_count: 0,
  owner_id: 'app_user:owner',
  workspace_id: 'workspace:personal',
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

describe('NotebooksPage', () => {
  beforeEach(() => {
    currentWorkspaceType = 'personal'
    activeNotebooks = [
      notebook({ id: 'notebook:personal', name: 'Personal notebook' }),
    ]
    archivedNotebooks = []
    publicNotebooks = [
      notebook({
        id: 'notebook:public',
        name: 'Public notebook',
        workspace_id: 'workspace:public',
        visibility: 'public',
      }),
    ]
  })

  it('groups personal workspace notebooks with public notebooks', () => {
    render(<NotebooksPage />)

    const personalGroup = screen.getByRole('region', { name: 'Personal notebooks' })
    expect(within(personalGroup).getByText('Personal notebook')).toBeInTheDocument()

    const publicGroup = screen.getByRole('region', { name: 'Public notebooks' })
    expect(within(publicGroup).getByText('Public notebook')).toBeInTheDocument()
  })

  it('labels current team workspace notebooks separately from public notebooks', () => {
    currentWorkspaceType = 'team'
    activeNotebooks = [
      notebook({
        id: 'notebook:team',
        name: 'Team notebook',
        workspace_id: 'workspace:team',
        visibility: 'team',
      }),
    ]

    render(<NotebooksPage />)

    const teamGroup = screen.getByRole('region', { name: 'Team notebooks' })
    expect(within(teamGroup).getByText('Team notebook')).toBeInTheDocument()
    expect(screen.getByRole('region', { name: 'Public notebooks' })).toBeInTheDocument()
  })
})
