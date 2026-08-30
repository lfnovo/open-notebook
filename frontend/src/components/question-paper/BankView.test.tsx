import { describe, expect, it, vi } from 'vitest'
import { render, screen, within } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BankView } from './BankView'

vi.mock('@/lib/hooks/use-question-paper', async () => {
  const actual = await vi.importActual<typeof import('@/lib/hooks/use-question-paper')>(
    '@/lib/hooks/use-question-paper',
  )
  const mediumQuestions = Array.from({ length: 21 }, (_, index) => ({
    id: `question_bank:${index}`,
    question: `Question ${index + 1}`,
    topic: 'SIP',
    type: 'mcq',
    difficulty: 'medium',
    answer: 'A',
    validated_cognitive_difficulty: 'medium',
    grade: '10',
  }))
  return {
    ...actual,
    useQuestionBank: () => ({ data: mediumQuestions, isLoading: false }),
    useBooks: () => ({
      data: [
        {
          book_id: 'question_book:4b46dax7tgo86c3sgaz0',
          display_name: 'PFH 2026 Grade 10',
          grade: '10',
          year: '2026',
          metadata_complete: true,
        },
      ],
      isLoading: false,
    }),
    useQuestionBooks: () => ({}),
  }
})

function renderBank() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <BankView />
    </QueryClientProvider>,
  )
}

describe('BankView filters', () => {
  it('shows filter labels, select placeholders, and summary card labels', () => {
    renderBank()

    const row1 = screen.getByTestId('bank-filter-row-1')
    const row2 = screen.getByTestId('bank-filter-row-2')
    expect(row1.children).toHaveLength(4)
    expect(row2.children).toHaveLength(4)

    expect(within(row1).getByText('Grade')).toBeInTheDocument()
    expect(within(row1).getByText('Year')).toBeInTheDocument()
    expect(within(row1).getByText('Book')).toBeInTheDocument()
    expect(within(row1).getByText('Chapter')).toBeInTheDocument()
    expect(within(row2).getByText('Difficulty')).toBeInTheDocument()
    expect(within(row2).getByText('Answer Type')).toBeInTheDocument()
    expect(within(row2).getByText('Batch ID')).toBeInTheDocument()
    expect(within(row2).getByText('Search')).toBeInTheDocument()

    expect(within(row1).getByText('Select Grade')).toBeInTheDocument()
    expect(within(row1).getByText('Select Year')).toBeInTheDocument()
    expect(within(row1).getByText('Select Book')).toBeInTheDocument()
    expect(within(row1).getByText('Select Chapter')).toBeInTheDocument()
    expect(within(row2).getByText('Select Difficulty')).toBeInTheDocument()
    expect(within(row2).getByText('Select Answer Type')).toBeInTheDocument()
    expect(within(row2).getByText('Select Batch ID')).toBeInTheDocument()

    const total = screen.getByTestId('bank-summary-total')
    expect(within(total).getByText('Total Questions')).toBeInTheDocument()
    expect(within(total).getByText('21')).toBeInTheDocument()

    const easy = screen.getByTestId('bank-summary-easy')
    expect(within(easy).getByText('Easy')).toBeInTheDocument()
    expect(within(easy).getByText('0')).toBeInTheDocument()

    const medium = screen.getByTestId('bank-summary-medium')
    expect(within(medium).getByText('Medium')).toBeInTheDocument()
    expect(within(medium).getByText('21')).toBeInTheDocument()

    const difficult = screen.getByTestId('bank-summary-difficult')
    expect(within(difficult).getByText('Difficult')).toBeInTheDocument()
    expect(within(difficult).getByText('0')).toBeInTheDocument()
  })
})
