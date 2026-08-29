import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { describe, it, expect, vi, beforeEach } from 'vitest'

import { AskAcrossSourcesDialog } from './AskAcrossSourcesDialog'
import { useSources } from '@/lib/hooks/use-sources'
import { commandsApi } from '@/lib/api/commands'

// useTranslation is mocked globally in setup.ts (t returns the key string)

vi.mock('@/lib/hooks/use-sources')
vi.mock('@/lib/api/commands', () => ({
  commandsApi: {
    submit: vi.fn(),
    getStatus: vi.fn(),
  },
}))

function renderDialog(notebookId = 'notebook:1') {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <AskAcrossSourcesDialog open onOpenChange={vi.fn()} notebookId={notebookId} />
    </QueryClientProvider>
  )
}

describe('AskAcrossSourcesDialog', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(useSources).mockReturnValue({
      data: [
        { id: 'source:1', title: 'Book One' },
        { id: 'source:2', title: 'Book Two' },
      ],
      isLoading: false,
    } as unknown as ReturnType<typeof useSources>)
  })

  it('lists every notebook source pre-checked', () => {
    renderDialog()

    expect(screen.getByText('Book One')).toBeInTheDocument()
    expect(screen.getByText('Book Two')).toBeInTheDocument()
    const checkboxes = screen.getAllByRole('checkbox')
    expect(checkboxes).toHaveLength(2)
    checkboxes.forEach((checkbox) => expect(checkbox).toBeChecked())
  })

  it('submits the selected sources as "full content" and the rest as "not in"', async () => {
    vi.mocked(commandsApi.submit).mockResolvedValue({ job_id: 'job:1', status: 'submitted' })

    renderDialog('notebook:1')

    // Uncheck the second source, then ask a question.
    fireEvent.click(screen.getAllByRole('checkbox')[1])
    fireEvent.change(screen.getByLabelText('askSources.questionLabel'), {
      target: { value: 'What do these say about compounding?' },
    })
    fireEvent.click(screen.getByText('askSources.submitBtn'))

    await waitFor(() => expect(commandsApi.submit).toHaveBeenCalledTimes(1))
    expect(commandsApi.submit).toHaveBeenCalledWith('ask_across_sources', 'open_notebook', {
      notebook_id: 'notebook:1',
      question: 'What do these say about compounding?',
      context_config: {
        sources: { 'source:1': 'full content', 'source:2': 'not in' },
        notes: {},
      },
    })
  })

  it('does not submit without a question', () => {
    renderDialog()

    fireEvent.click(screen.getByText('askSources.submitBtn'))

    expect(commandsApi.submit).not.toHaveBeenCalled()
  })

  it('does not submit with no sources selected', () => {
    renderDialog()

    screen.getAllByRole('checkbox').forEach((checkbox) => fireEvent.click(checkbox))
    fireEvent.change(screen.getByLabelText('askSources.questionLabel'), {
      target: { value: 'A question' },
    })
    fireEvent.click(screen.getByText('askSources.submitBtn'))

    expect(commandsApi.submit).not.toHaveBeenCalled()
  })
})
