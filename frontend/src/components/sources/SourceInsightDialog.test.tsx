import { fireEvent, render, screen, within } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { SourceInsightDialog } from './SourceInsightDialog'
import { useInsight, useSaveInsightAsNote } from '@/lib/hooks/use-insights'
import { useNotebooks } from '@/lib/hooks/use-notebooks'

// useTranslation is mocked globally in setup.ts (t returns the key string)

vi.mock('@/lib/hooks/use-insights', () => ({
  useInsight: vi.fn(),
  useSaveInsightAsNote: vi.fn(),
}))

vi.mock('@/lib/hooks/use-notebooks', () => ({
  useNotebooks: vi.fn(),
}))

vi.mock('@/components/ui/select', () => ({
  Select: ({ children, onValueChange, value }: React.PropsWithChildren<{
    value: string
    onValueChange: (value: string) => void
  }>) => (
    <select aria-label="notebook" value={value} onChange={event => onValueChange(event.target.value)}>
      <option value="" />
      {children}
    </select>
  ),
  SelectTrigger: ({ children }: React.PropsWithChildren) => <>{children}</>,
  SelectValue: () => null,
  SelectContent: ({ children }: React.PropsWithChildren) => <>{children}</>,
  SelectItem: ({ children, value }: React.PropsWithChildren<{ value: string }>) => (
    <option value={value}>{children}</option>
  ),
}))

vi.mock('@/lib/hooks/use-modal-manager', () => ({
  useModalManager: () => ({ openModal: vi.fn() }),
}))

const mockUseInsight = vi.mocked(useInsight)
const mockUseSaveInsightAsNote = vi.mocked(useSaveInsightAsNote)
const mockUseNotebooks = vi.mocked(useNotebooks)
const mockSaveAsNote = vi.fn()

const notFoundError = Object.assign(new Error('Request failed with status code 404'), {
  isAxiosError: true,
  response: { status: 404 },
})

const networkError = Object.assign(new Error('Network Error'), {
  isAxiosError: true,
  response: undefined,
})

type UseInsightResult = ReturnType<typeof useInsight>

const asResult = (value: Partial<UseInsightResult>) => value as UseInsightResult

const loadedInsight = asResult({
  data: {
    id: 'insight-1',
    source_id: 'source:1',
    insight_type: 'summary',
    content: 'Fetched insight content',
    created: null,
    updated: null,
  },
  isLoading: false,
  isError: false,
  error: null,
})

describe('SourceInsightDialog', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockUseSaveInsightAsNote.mockReturnValue(
      { mutate: mockSaveAsNote, isPending: false } as unknown as ReturnType<typeof useSaveInsightAsNote>
    )
    mockUseNotebooks.mockReturnValue(
      { data: [], isLoading: false } as unknown as ReturnType<typeof useNotebooks>
    )
  })

  it('shows the shared not-found state when the insight returns 404', () => {
    mockUseInsight.mockReturnValue(
      asResult({ data: undefined, isLoading: false, isError: true, error: notFoundError })
    )

    render(
      <SourceInsightDialog
        open={true}
        onOpenChange={vi.fn()}
        insight={{ id: 'insight-1', insight_type: '', content: '' }}
      />
    )

    expect(screen.getByTestId('content-unavailable')).toBeInTheDocument()
    expect(screen.getByText('common.contentUnavailable.notFoundTitle')).toBeInTheDocument()
    expect(screen.getByText('common.contentUnavailable.notFoundDescription')).toBeInTheDocument()
    // No ghost fallback content and no "view source" affordance
    expect(screen.queryByText('sources.viewSource')).not.toBeInTheDocument()
  })

  it('shows the shared load-error state for non-404 failures', () => {
    mockUseInsight.mockReturnValue(
      asResult({ data: undefined, isLoading: false, isError: true, error: networkError })
    )

    render(
      <SourceInsightDialog
        open={true}
        onOpenChange={vi.fn()}
        insight={{ id: 'insight-1', insight_type: '', content: '' }}
      />
    )

    expect(screen.getByText('common.contentUnavailable.errorTitle')).toBeInTheDocument()
    expect(
      screen.queryByText('common.contentUnavailable.notFoundTitle')
    ).not.toBeInTheDocument()
  })

  it('closes the dialog from the not-found state close button', () => {
    mockUseInsight.mockReturnValue(
      asResult({ data: undefined, isLoading: false, isError: true, error: notFoundError })
    )
    const onOpenChange = vi.fn()

    render(
      <SourceInsightDialog
        open={true}
        onOpenChange={onOpenChange}
        insight={{ id: 'insight-1', insight_type: '', content: '' }}
      />
    )

    within(screen.getByTestId('content-unavailable')).getByText('common.close').click()
    expect(onOpenChange).toHaveBeenCalledWith(false)
  })

  it('renders the insight content when the fetch succeeds', () => {
    mockUseInsight.mockReturnValue(
      asResult({
        data: {
          id: 'insight-1',
          source_id: 'source:1',
          insight_type: 'summary',
          content: 'Fetched insight content',
          created: null,
          updated: null,
        },
        isLoading: false,
        isError: false,
        error: null,
      })
    )

    render(
      <SourceInsightDialog
        open={true}
        onOpenChange={vi.fn()}
        insight={{ id: 'insight-1', insight_type: '', content: '' }}
      />
    )

    expect(screen.getByText('Fetched insight content')).toBeInTheDocument()
    expect(screen.queryByTestId('content-unavailable')).not.toBeInTheDocument()
  })

  it('saves the insight to the given notebook without a picker', () => {
    mockUseInsight.mockReturnValue(loadedInsight)

    render(
      <SourceInsightDialog
        open={true}
        onOpenChange={vi.fn()}
        insight={{ id: 'insight-1', insight_type: '', content: '' }}
        notebookId="notebook:1"
      />
    )

    expect(screen.queryByRole('combobox', { name: 'notebook' })).not.toBeInTheDocument()
    expect(mockUseNotebooks).not.toHaveBeenCalled()

    fireEvent.click(screen.getByRole('button', { name: 'sources.saveAsNote' }))
    expect(mockSaveAsNote).toHaveBeenCalledWith({
      insightId: 'source_insight:insight-1',
      notebookId: 'notebook:1',
    })
  })

  it('asks for a notebook when there is no notebook context and saves to the chosen one', () => {
    mockUseInsight.mockReturnValue(loadedInsight)
    mockUseNotebooks.mockReturnValue({
      data: [
        { id: 'notebook:1', name: 'First' },
        { id: 'notebook:2', name: 'Second' },
      ],
      isLoading: false,
    } as unknown as ReturnType<typeof useNotebooks>)

    render(
      <SourceInsightDialog
        open={true}
        onOpenChange={vi.fn()}
        insight={{ id: 'insight-1', insight_type: '', content: '' }}
      />
    )

    const saveButton = screen.getByRole('button', { name: 'sources.saveAsNote' })
    expect(saveButton).toBeDisabled()

    fireEvent.change(screen.getByRole('combobox', { name: 'notebook' }), {
      target: { value: 'notebook:2' },
    })
    fireEvent.click(saveButton)

    expect(mockSaveAsNote).toHaveBeenCalledWith({
      insightId: 'source_insight:insight-1',
      notebookId: 'notebook:2',
    })
  })

  it('preselects the notebook when there is only one', () => {
    mockUseInsight.mockReturnValue(loadedInsight)
    mockUseNotebooks.mockReturnValue({
      data: [{ id: 'notebook:1', name: 'Only' }],
      isLoading: false,
    } as unknown as ReturnType<typeof useNotebooks>)

    render(
      <SourceInsightDialog
        open={true}
        onOpenChange={vi.fn()}
        insight={{ id: 'insight-1', insight_type: '', content: '' }}
      />
    )

    fireEvent.click(screen.getByRole('button', { name: 'sources.saveAsNote' }))
    expect(mockSaveAsNote).toHaveBeenCalledWith({
      insightId: 'source_insight:insight-1',
      notebookId: 'notebook:1',
    })
  })
})
