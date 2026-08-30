import { describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BankBatchReview } from './BankBatchReview'

const questions = [
  {
    id: 'question_bank:a',
    question: 'What is a Systematic Investment Plan (SIP)?',
    topic: 'Mutual Funds',
    type: 'mcq',
    difficulty: 'medium',
    answer: 'B',
    explanation: 'SIP invests a fixed amount at regular intervals.',
    options: ['One-time', 'Fixed amount regularly', 'Stocks only', 'No lock-in', 'Govt scheme'],
    correct_indices: [1],
    answer_type: 'single_correct',
    validated_cognitive_difficulty: 'medium',
    difficulty_score: 15,
    validation_status: 'passed',
  },
  {
    id: 'question_bank:b',
    question: 'Which statements about SIPs are true?',
    topic: 'Mutual Funds',
    type: 'multi_correct',
    difficulty: 'medium',
    answer: 'B, D',
    explanation: 'Regular investing and no mandatory lock-in apply.',
    options: ['One-time', 'Fixed amount regularly', 'Stocks only', 'No lock-in', 'Govt scheme'],
    correct_indices: [1, 3],
    answer_type: 'multiple_correct',
    validated_cognitive_difficulty: 'medium',
    difficulty_score: 16,
    validation_status: 'passed',
  },
]

vi.mock('@/lib/hooks/use-question-paper', async () => {
  const actual = await vi.importActual<typeof import('@/lib/hooks/use-question-paper')>(
    '@/lib/hooks/use-question-paper',
  )
  return {
    ...actual,
    useBankBatchResult: () => ({
      data: {
        batch_id: 'question_bank_batch:qkozkavx2rfkorgleo0h',
        status: 'completed_partial',
        grade: '10',
        book_id: 'question_book:4b46dax7tgo86c3sgaz0',
        chapter: 2,
        difficulty: 'medium',
        questions,
      },
      isLoading: false,
      isError: false,
    }),
    useQuestionBooks: () => ({
      'question_book:4b46dax7tgo86c3sgaz0': 'PFH 2026 Grade 10',
    }),
  }
})

function renderReview() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <BankBatchReview batchId="question_bank_batch:qkozkavx2rfkorgleo0h" />
    </QueryClientProvider>,
  )
}

describe('BankBatchReview', () => {
  it('navigates from history and reviews single and multiple correct questions', () => {
    renderReview()

    expect(screen.getByRole('link', { name: /Back to history/ })).toHaveAttribute(
      'href',
      '/question-paper?tab=bank',
    )
    expect(screen.getByText('Review Bank Questions')).toBeInTheDocument()
    expect(screen.getByText(/Grade 10/)).toBeInTheDocument()

    expect(screen.getAllByText('What is a Systematic Investment Plan (SIP)?').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Single Correct').length).toBeGreaterThan(0)
    expect(screen.getByText('15')).toBeInTheDocument()
    expect(screen.queryByRole('textbox')).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: /Question 2/ }))
    expect(screen.getAllByText('Which statements about SIPs are true?').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Multiple Correct').length).toBeGreaterThan(0)
    expect(screen.getByText('B, D')).toBeInTheDocument()
    expect(screen.getAllByText('Correct').length).toBeGreaterThanOrEqual(2)
  })
})
