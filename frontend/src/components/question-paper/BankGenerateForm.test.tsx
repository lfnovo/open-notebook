import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BankGenerateForm } from './BankGenerateForm'

vi.mock('@/lib/hooks/use-question-paper', async () => {
  const actual = await vi.importActual<typeof import('@/lib/hooks/use-question-paper')>(
    '@/lib/hooks/use-question-paper',
  )
  return {
    ...actual,
    useBooks: () => ({
      data: [
        {
          book_id: 'question_book:4b46dax7tgo86c3sgaz0',
          display_name: 'PFH 2026 Grade 10',
          grade: '10',
          year: '2026',
          subject: 'Financial Literacy',
          chapter_count: 4,
          metadata_complete: true,
        },
      ],
      isLoading: false,
    }),
    useGenerateBankBatch: () => ({
      mutate: vi.fn(),
      isPending: false,
    }),
    useBankBatchStatus: () => ({ data: undefined }),
  }
})

function renderForm() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={client}>
      <BankGenerateForm />
    </QueryClientProvider>,
  )
}

const GENERATE_LABELS = [
  'Grade',
  'Year',
  'Book',
  'Chapter',
  'Difficulty',
  'Total Questions',
  'Single Correct',
  'Multiple Correct',
]

describe('BankGenerateForm', () => {
  it('renders bank generate fields and keeps submit disabled until counts match', () => {
    renderForm()
    expect(screen.getByLabelText('Total Questions')).toBeInTheDocument()
    expect(screen.getByLabelText('Single Correct')).toBeInTheDocument()
    expect(screen.getByLabelText('Multiple Correct')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Generate Bank Questions' })).toBeDisabled()
    expect(screen.getByText('This adds questions to the bank. It does not create a final exam paper.')).toBeInTheDocument()
  })

  it('keeps labels visible and shows select placeholders before values are chosen', () => {
    renderForm()
    for (const label of GENERATE_LABELS) {
      expect(screen.getByText(label)).toBeInTheDocument()
    }
    expect(screen.getByText('Select Grade')).toBeInTheDocument()
    expect(screen.getByText('Select Year')).toBeInTheDocument()
    expect(screen.getByText('Select Book')).toBeInTheDocument()
    expect(screen.getByText('Select Chapter')).toBeInTheDocument()
    expect(screen.getByText('Select Difficulty')).toBeInTheDocument()

    const row1 = screen.getByTestId('bank-generate-row-1')
    const row2 = screen.getByTestId('bank-generate-row-2')
    expect(row1).toHaveClass('grid', 'sm:grid-cols-2', 'lg:grid-cols-4')
    expect(row2).toHaveClass('grid', 'sm:grid-cols-2', 'lg:grid-cols-4')
    expect(row1.children).toHaveLength(4)
    expect(row2.children).toHaveLength(4)

    screen.getAllByRole('combobox').forEach((control) => {
      expect(control).toHaveClass('w-full', 'h-9')
    })
  })
})
