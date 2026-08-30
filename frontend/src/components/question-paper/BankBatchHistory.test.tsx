import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BankBatchHistory } from './BankBatchHistory'

vi.mock('@/lib/hooks/use-question-paper', async () => {
  const actual = await vi.importActual<typeof import('@/lib/hooks/use-question-paper')>(
    '@/lib/hooks/use-question-paper',
  )
  return {
    ...actual,
    useBankBatches: () => ({
      data: [
        {
          batch_id: 'question_bank_batch:qkozkavx2rfkorgleo0h',
          grade: '10',
          book_id: 'question_book:4b46dax7tgo86c3sgaz0',
          chapter: 2,
          difficulty: 'medium',
          requested: 15,
          accepted: 12,
          status: 'completed_partial',
          created: '2026-08-30T01:00:00Z',
          saved_question_ids: ['question_bank:a'],
          stop_reason: 'catalog_exhausted',
          error_message: 'Stopped after 12/15 accepted; catalog exhausted.',
        },
        {
          batch_id: 'question_bank_batch:running',
          grade: '10',
          book_id: 'question_book:4b46dax7tgo86c3sgaz0',
          chapter: 1,
          difficulty: 'easy',
          requested: 5,
          accepted: 0,
          status: 'running',
          created: '2026-08-30T02:00:00Z',
          saved_question_ids: [],
        },
      ],
      isLoading: false,
    }),
    useQuestionBooks: () => ({
      'question_book:4b46dax7tgo86c3sgaz0': 'PFH 2026 Grade 10',
    }),
  }
})

function renderHistory() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <BankBatchHistory />
    </QueryClientProvider>,
  )
}

describe('BankBatchHistory', () => {
  it('renders batch history columns and disables actions while running', () => {
    renderHistory()
    expect(screen.getByText('Bank Generation History')).toBeInTheDocument()
    expect(screen.getAllByText('PFH 2026 Grade 10').length).toBeGreaterThan(0)
    expect(screen.getByText('Chapter 2')).toBeInTheDocument()
    expect(screen.getByText('question_bank_batch:qkozkavx2rfkorgleo0h')).toBeInTheDocument()

    expect(screen.getByText('Completed (partial)')).toBeInTheDocument()
    expect(screen.getByText('Question catalog was exhausted')).toBeInTheDocument()
    expect(screen.queryByText('Failed')).not.toBeInTheDocument()
    expect(screen.queryByText('Stopped after 12/15 accepted; catalog exhausted.')).not.toBeInTheDocument()

    const viewLinks = screen.getAllByRole('link', { name: 'View questions' })
    const exportButtons = screen.getAllByRole('button', { name: /Download Excel/ })
    expect(viewLinks).toHaveLength(1)
    expect(viewLinks[0]).toHaveAttribute(
      'href',
      '/question-paper/bank/question_bank_batch%3Aqkozkavx2rfkorgleo0h',
    )
    expect(exportButtons[0]).not.toBeDisabled()
    expect(screen.getByRole('button', { name: 'View questions' })).toBeDisabled()
    expect(exportButtons[1]).toBeDisabled()
  })
})
