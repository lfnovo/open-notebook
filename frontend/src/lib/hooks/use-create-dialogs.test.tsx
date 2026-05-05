import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

vi.unmock('@/lib/hooks/use-create-dialogs')

vi.mock('@/components/sources/AddSourceDialog', () => ({
  AddSourceDialog: ({ open }: { open: boolean }) => (
    <div data-testid="source-dialog">source:{String(open)}</div>
  ),
}))

vi.mock('@/components/notebooks/CreateNotebookDialog', () => ({
  CreateNotebookDialog: ({ open }: { open: boolean }) => (
    <div data-testid="notebook-dialog">notebook:{String(open)}</div>
  ),
}))

vi.mock('@/components/podcasts/GeneratePodcastDialog', () => ({
  GeneratePodcastDialog: ({ open }: { open: boolean }) => (
    <div data-testid="podcast-dialog">podcast:{String(open)}</div>
  ),
}))

describe('CreateDialogsProvider', () => {
  it('does not mount create dialogs until each dialog is opened', async () => {
    const { CreateDialogsProvider, useCreateDialogs } = await import('./use-create-dialogs')
    function DialogButtons() {
      const { openSourceDialog, openNotebookDialog, openPodcastDialog } = useCreateDialogs()

      return (
        <>
          <button type="button" onClick={openSourceDialog}>
            source
          </button>
          <button type="button" onClick={openNotebookDialog}>
            notebook
          </button>
          <button type="button" onClick={openPodcastDialog}>
            podcast
          </button>
        </>
      )
    }

    render(
      <CreateDialogsProvider>
        <DialogButtons />
      </CreateDialogsProvider>
    )

    expect(screen.queryByTestId('source-dialog')).not.toBeInTheDocument()
    expect(screen.queryByTestId('notebook-dialog')).not.toBeInTheDocument()
    expect(screen.queryByTestId('podcast-dialog')).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'source' }))

    expect(screen.getByTestId('source-dialog')).toHaveTextContent('source:true')
    expect(screen.queryByTestId('notebook-dialog')).not.toBeInTheDocument()
    expect(screen.queryByTestId('podcast-dialog')).not.toBeInTheDocument()
  })
})
