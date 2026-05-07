import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { NotebookResponse } from '@/lib/types/api'
import { NotebookHeader } from './NotebookHeader'

vi.mock('@/lib/hooks/use-notebooks', () => ({
  useUpdateNotebook: vi.fn(() => ({
    mutate: vi.fn(),
    mutateAsync: vi.fn(),
  })),
}))

vi.mock('./NotebookDeleteDialog', () => ({
  NotebookDeleteDialog: () => null,
}))

vi.mock('./NotebookMoveDialog', () => ({
  NotebookMoveDialog: () => null,
}))

const notebook = (overrides: Partial<NotebookResponse> = {}): NotebookResponse => ({
  id: 'notebook:public',
  name: 'Public notebook',
  description: '',
  archived: false,
  created: '2026-05-05T00:00:00Z',
  updated: '2026-05-05T00:00:00Z',
  source_count: 1,
  note_count: 1,
  visibility: 'public',
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

describe('NotebookHeader', () => {
  it('hides lifecycle actions when the notebook is read-only', () => {
    render(
      <NotebookHeader
        notebook={notebook()}
        canUpdateNotebook={false}
        canDeleteNotebook={false}
        canMoveNotebook={false}
      />
    )

    expect(screen.queryByRole('button', { name: /Move/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Archive/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Delete/i })).not.toBeInTheDocument()
  })

  it('shows lifecycle actions when the user can manage the notebook', () => {
    render(
      <NotebookHeader
        notebook={notebook({
          visibility: 'private',
          capabilities: undefined,
        })}
        canUpdateNotebook={true}
        canDeleteNotebook={true}
        canMoveNotebook={true}
      />
    )

    expect(screen.getByRole('button', { name: /Move/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Archive/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Delete/i })).toBeInTheDocument()
  })
})
