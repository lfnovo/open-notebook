import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { NoteResponse, ResourceCapabilities } from '@/lib/types/api'
import { NotesColumn } from './NotesColumn'

vi.mock('@/lib/hooks/use-notes', () => ({
  useDeleteNote: () => ({
    mutateAsync: vi.fn(),
    isPending: false,
  }),
}))

vi.mock('@/components/notebooks/CollapsibleColumn', () => ({
  CollapsibleColumn: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  createCollapseButton: () => null,
}))

vi.mock('./NoteEditorDialog', () => ({
  NoteEditorDialog: ({ open, note }: { open: boolean; note?: NoteResponse }) =>
    open ? <div data-testid="note-editor">{note?.id ?? 'new'}</div> : null,
}))

vi.mock('@/components/common/ConfirmDialog', () => ({
  ConfirmDialog: () => null,
}))

const capabilities = (overrides: Partial<ResourceCapabilities>): ResourceCapabilities => ({
  can_read: true,
  can_update: false,
  can_delete: false,
  can_share: false,
  can_manage: false,
  can_create_source: false,
  can_remove_source: false,
  can_create_note: false,
  can_process: false,
  ...overrides,
})

const note = (overrides: Partial<NoteResponse>): NoteResponse => ({
  id: 'note:base',
  title: 'Readonly note',
  content: 'Body',
  note_type: 'human',
  created: '2026-05-06T00:00:00Z',
  updated: '2026-05-06T00:00:00Z',
  capabilities: capabilities({}),
  ...overrides,
})

describe('NotesColumn', () => {
  it('allows team members to create notes when notebook capability allows it', () => {
    render(
      <NotesColumn
        notes={[]}
        isLoading={false}
        notebookId="notebook:team"
        canManageNotebook={false}
        canCreateNote={true}
      />
    )

    expect(screen.getByRole('button', { name: /Write Note/i })).not.toBeDisabled()
  })

  it('disables note deletion from note capabilities', () => {
    render(
      <NotesColumn
        notes={[note({ id: 'note:readonly' })]}
        isLoading={false}
        notebookId="notebook:team"
        canManageNotebook={true}
      />
    )

    expect(screen.getByRole('button', { name: /Actions/i })).toBeDisabled()
  })

  it('does not open the editor for readonly notes', () => {
    render(
      <NotesColumn
        notes={[note({ id: 'note:readonly' })]}
        isLoading={false}
        notebookId="notebook:team"
        canManageNotebook={true}
      />
    )

    fireEvent.click(screen.getByText('Readonly note'))

    expect(screen.queryByTestId('note-editor')).not.toBeInTheDocument()
  })
})
