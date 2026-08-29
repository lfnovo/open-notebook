import { render, screen, fireEvent, waitFor, act } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { describe, it, expect, vi, beforeEach } from 'vitest'

import { AskAcrossSourcesDialog } from './AskAcrossSourcesDialog'
import { useSources } from '@/lib/hooks/use-sources'
import { commandsApi } from '@/lib/api/commands'

vi.mock('@/lib/hooks/use-sources')
vi.mock('@/lib/api/commands', () => ({
  commandsApi: {
    submit: vi.fn(),
    getStatus: vi.fn(),
  },
}))

function renderDialog() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <AskAcrossSourcesDialog open onOpenChange={vi.fn()} notebookId="notebook:1" />
    </QueryClientProvider>
  )
}

describe('AskAcrossSourcesDialog polling', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(useSources).mockReturnValue({
      data: [{ id: 'source:1', title: 'Book One' }],
      isLoading: false,
    } as unknown as ReturnType<typeof useSources>)
  })

  it('keeps polling every 3s while the job is running, not just once', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    vi.mocked(commandsApi.submit).mockResolvedValue({ job_id: 'job:1', status: 'submitted' })
    vi.mocked(commandsApi.getStatus).mockResolvedValue({
      job_id: 'job:1',
      status: 'running',
      result: null,
    })

    renderDialog()
    fireEvent.change(screen.getByLabelText('askSources.questionLabel'), {
      target: { value: 'A real question' },
    })
    fireEvent.click(screen.getByText('askSources.submitBtn'))

    await waitFor(() => expect(commandsApi.getStatus).toHaveBeenCalledTimes(1))

    // Advance past 3 more poll intervals - if refetchInterval stopped after
    // the first fetch (the real bug this test is pinned to), the call count
    // will still be 1 here instead of growing.
    for (let i = 0; i < 3; i++) {
      await act(async () => {
        await vi.advanceTimersByTimeAsync(3100)
      })
    }

    expect(commandsApi.getStatus.mock.calls.length).toBeGreaterThan(1)

    vi.useRealTimers()
  })
})
