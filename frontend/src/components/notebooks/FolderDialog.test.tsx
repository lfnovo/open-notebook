import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { AxiosError } from 'axios'

import { FolderDialog } from './FolderDialog'

const createMutateAsync = vi.fn()
const renameMutateAsync = vi.fn()
vi.mock('@/lib/hooks/use-folders', async () => {
  const { isAxiosError } = await import('axios')
  return {
    isDuplicateFolderError: (e: unknown) => isAxiosError(e) && e.response?.status === 409,
    useCreateFolder: () => ({ mutateAsync: createMutateAsync, isPending: false }),
    useRenameFolder: () => ({ mutateAsync: renameMutateAsync, isPending: false }),
  }
})

vi.mock('@/lib/hooks/use-sections', () => ({
  useSections: () => ({
    data: [
      { id: 'section:1', name: 'Personal', folder_count: 0 },
      { id: 'section:2', name: 'Work', folder_count: 0 },
    ],
  }),
}))

const input = () => screen.getByLabelText(/folders.nameLabel/)
const submit = () => screen.getByRole('button', { name: 'folders.create' })

function conflict() {
  const error = new AxiosError('conflict')
  error.response = { status: 409, data: {}, statusText: '', headers: {}, config: {} as never }
  return error
}

describe('FolderDialog', () => {
  beforeEach(() => vi.clearAllMocks())

  it('disables submit for empty and over-long names', () => {
    render(<FolderDialog open onOpenChange={vi.fn()} />)
    expect(submit()).toBeDisabled()

    fireEvent.change(input(), { target: { value: 'a'.repeat(81) } })
    expect(submit()).toBeDisabled()
    expect(screen.getByText('folders.nameTooLong')).toBeInTheDocument()

    fireEvent.change(input(), { target: { value: 'a'.repeat(80) } })
    expect(submit()).toBeEnabled()
  })

  it('creates with the trimmed name, closes and reports the folder', async () => {
    const saved = { id: 'folder:1', name: 'Research' }
    createMutateAsync.mockResolvedValue(saved)
    const onOpenChange = vi.fn()
    const onSaved = vi.fn()
    render(<FolderDialog open onOpenChange={onOpenChange} onSaved={onSaved} />)

    fireEvent.change(input(), { target: { value: '  Research  ' } })
    fireEvent.click(submit())

    await waitFor(() => expect(createMutateAsync).toHaveBeenCalledWith({ name: 'Research', sectionId: null }))
    await waitFor(() => expect(onSaved).toHaveBeenCalledWith(saved))
    expect(onOpenChange).toHaveBeenCalledWith(false)
  })

  it('shows the duplicate-name error on 409 and stays open', async () => {
    createMutateAsync.mockRejectedValue(conflict())
    const onOpenChange = vi.fn()
    render(<FolderDialog open onOpenChange={onOpenChange} />)

    fireEvent.change(input(), { target: { value: 'Research' } })
    fireEvent.click(submit())

    expect(await screen.findByText('folders.duplicateName')).toBeInTheDocument()
    expect(onOpenChange).not.toHaveBeenCalled()

    fireEvent.change(input(), { target: { value: 'Research 2' } })
    expect(screen.queryByText('folders.duplicateName')).not.toBeInTheDocument()
  })

  it('renames an existing folder', async () => {
    renameMutateAsync.mockResolvedValue({ id: 'folder:1', name: 'New' })
    const folder = {
      id: 'folder:1',
      name: 'Old',
      created: '',
      updated: '',
      notebook_count: 0,
    }
    render(<FolderDialog open onOpenChange={vi.fn()} folder={folder} />)
    expect(input()).toHaveValue('Old')

    fireEvent.change(input(), { target: { value: 'New' } })
    fireEvent.click(screen.getByRole('button', { name: 'folders.rename' }))

    await waitFor(() =>
      expect(renameMutateAsync).toHaveBeenCalledWith({ id: 'folder:1', name: 'New', sectionId: null })
    )
    expect(createMutateAsync).not.toHaveBeenCalled()
  })

  it('creates a folder inside the chosen section', async () => {
    createMutateAsync.mockResolvedValue({ id: 'folder:1', name: 'True crime' })
    render(<FolderDialog open onOpenChange={vi.fn()} defaultSectionId="section:1" />)

    expect(screen.getByLabelText('sections.sectionLabel')).toHaveValue('section:1')
    fireEvent.change(input(), { target: { value: 'True crime' } })
    fireEvent.click(submit())

    await waitFor(() =>
      expect(createMutateAsync).toHaveBeenCalledWith({ name: 'True crime', sectionId: 'section:1' })
    )
  })

  it('moves a folder to another section when renaming', async () => {
    renameMutateAsync.mockResolvedValue({ id: 'folder:1', name: 'Same' })
    const folder = {
      id: 'folder:1',
      name: 'Same',
      created: '',
      updated: '',
      notebook_count: 0,
      section_id: 'section:1',
    }
    render(<FolderDialog open onOpenChange={vi.fn()} folder={folder} />)

    fireEvent.change(screen.getByLabelText('sections.sectionLabel'), {
      target: { value: 'section:2' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'folders.rename' }))

    await waitFor(() =>
      expect(renameMutateAsync).toHaveBeenCalledWith({
        id: 'folder:1',
        name: 'Same',
        sectionId: 'section:2',
      })
    )
  })
})
