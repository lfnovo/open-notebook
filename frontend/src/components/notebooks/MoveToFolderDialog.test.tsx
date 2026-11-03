import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'

import { MoveToFolderDialog } from './MoveToFolderDialog'
import type { NotebookResponse } from '@/lib/types/api'

const moveAsync = vi.fn()
vi.mock('@/lib/hooks/use-sections', () => ({
  useSections: () => ({ data: [] }),
}))
vi.mock('@/lib/hooks/use-folders', () => ({
  useFolders: () => ({
    data: [
      { id: 'folder:a', name: 'Alpha', created: '', updated: '', notebook_count: 1 },
      { id: 'folder:b', name: 'Beta', created: '', updated: '', notebook_count: 0 },
    ],
  }),
  useMoveNotebookToFolder: () => ({ mutateAsync: moveAsync, isPending: false }),
  // used by the nested FolderDialog
  isDuplicateFolderError: () => false,
  useCreateFolder: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useRenameFolder: () => ({ mutateAsync: vi.fn(), isPending: false }),
}))

const notebook = (folder_id: string | null): NotebookResponse => ({
  id: 'notebook:1',
  name: 'My notebook',
  description: '',
  archived: false,
  created: '',
  updated: '',
  source_count: 0,
  note_count: 0,
  folder_id,
})

describe('MoveToFolderDialog', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    moveAsync.mockResolvedValue({})
  })

  it('sends the folder id when choosing a folder', async () => {
    const onOpenChange = vi.fn()
    render(<MoveToFolderDialog open onOpenChange={onOpenChange} notebook={notebook(null)} />)
    fireEvent.click(screen.getByRole('button', { name: /Beta/ }))

    await waitFor(() =>
      expect(moveAsync).toHaveBeenCalledWith({ notebookId: 'notebook:1', folderId: 'folder:b' })
    )
    expect(onOpenChange).toHaveBeenCalledWith(false)
  })

  it('sends null when choosing "No folder"', async () => {
    render(<MoveToFolderDialog open onOpenChange={vi.fn()} notebook={notebook('folder:a')} />)
    fireEvent.click(screen.getByRole('button', { name: /folders.noFolder/ }))

    await waitFor(() =>
      expect(moveAsync).toHaveBeenCalledWith({ notebookId: 'notebook:1', folderId: null })
    )
  })

  it('does not call the API when choosing the current folder', () => {
    const onOpenChange = vi.fn()
    render(<MoveToFolderDialog open onOpenChange={onOpenChange} notebook={notebook('folder:a')} />)
    fireEvent.click(screen.getByRole('button', { name: /Alpha/ }))
    expect(moveAsync).not.toHaveBeenCalled()
    expect(onOpenChange).toHaveBeenCalledWith(false)
  })

  it('offers a New folder... option that opens the folder dialog', () => {
    render(<MoveToFolderDialog open onOpenChange={vi.fn()} notebook={notebook(null)} />)
    fireEvent.click(screen.getByRole('button', { name: /folders.newFolderEllipsis/ }))
    expect(screen.getByLabelText(/folders.nameLabel/)).toBeInTheDocument()
  })
})
