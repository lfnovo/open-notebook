import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { SaveToNotebooksDialog } from './SaveToNotebooksDialog'
import { NotebookResponse, ResourceCapabilities } from '@/lib/types/api'

const mockHooks = vi.hoisted(() => ({
  notebooks: [] as NotebookResponse[],
  isLoading: false,
  mutateAsync: vi.fn(),
}))

vi.mock('@/lib/hooks/use-notebooks', () => ({
  useNotebooks: () => ({
    data: mockHooks.notebooks,
    isLoading: mockHooks.isLoading,
  }),
}))

vi.mock('@/lib/hooks/use-notes', () => ({
  useCreateNote: () => ({
    mutateAsync: mockHooks.mutateAsync,
    isPending: false,
  }),
}))

vi.mock('sonner', () => ({
  toast: {
    error: vi.fn(),
    success: vi.fn(),
  },
}))

const capabilities = (canCreateNote: boolean): ResourceCapabilities => ({
  can_read: true,
  can_update: false,
  can_delete: false,
  can_share: false,
  can_manage: false,
  can_create_source: false,
  can_remove_source: false,
  can_create_note: canCreateNote,
  can_process: false,
})

const notebook = (
  id: string,
  name: string,
  canCreateNote: boolean,
): NotebookResponse => ({
  id,
  name,
  description: '',
  archived: false,
  created: '2026-05-07T00:00:00Z',
  updated: '2026-05-07T00:00:00Z',
  source_count: 0,
  note_count: 0,
  visibility: canCreateNote ? 'private' : 'public',
  capabilities: capabilities(canCreateNote),
})

describe('SaveToNotebooksDialog', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockHooks.isLoading = false
    mockHooks.notebooks = []
  })

  it('only lists notebooks where the actor can create notes', () => {
    mockHooks.notebooks = [
      notebook('notebook:personal', 'Personal notebook', true),
      notebook('notebook:public', 'Readonly public notebook', false),
    ]

    render(
      <SaveToNotebooksDialog
        open
        onOpenChange={vi.fn()}
        question="BSD是什么？"
        answer="Final answer"
      />
    )

    expect(screen.getByRole('checkbox', { name: 'Personal notebook' })).toBeInTheDocument()
    expect(screen.queryByText('Readonly public notebook')).not.toBeInTheDocument()
  })
})
