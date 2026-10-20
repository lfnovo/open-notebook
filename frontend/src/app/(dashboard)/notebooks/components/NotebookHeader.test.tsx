import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { NotebookResponse } from '@/lib/types/api'
import { NotebookHeader } from './NotebookHeader'

const mutateAsync = vi.fn()

vi.mock('@/lib/hooks/use-notebooks', () => ({
  useUpdateNotebook: () => ({ mutateAsync, mutate: vi.fn() }),
}))

vi.mock('./NotebookDeleteDialog', () => ({
  NotebookDeleteDialog: () => null,
}))

const notebook: NotebookResponse = {
  id: 'notebook:n1',
  name: 'My notebook',
  description: 'old description',
  archived: false,
  created: '2026-01-01T00:00:00Z',
  updated: '2026-01-02T00:00:00Z',
  source_count: 0,
  note_count: 0,
}

describe('NotebookHeader', () => {
  beforeEach(() => {
    mutateAsync.mockReset()
    mutateAsync.mockResolvedValue(undefined)
  })

  // An empty description used to be sent as `undefined`, i.e. dropped from the
  // update, so the old text came back after a refresh (#1396).
  it('sends an empty description when the description is cleared', async () => {
    render(<NotebookHeader notebook={notebook} />)

    fireEvent.click(screen.getByText('old description'))
    const textarea = screen.getByDisplayValue('old description')
    fireEvent.change(textarea, { target: { value: '' } })
    fireEvent.blur(textarea)

    await waitFor(() =>
      expect(mutateAsync).toHaveBeenCalledWith({
        id: 'notebook:n1',
        data: { description: '' },
      })
    )
  })
})
