import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import SearchPage from './page'

const mockSearchParamsState = vi.hoisted(() => ({
  value: '',
}))

const mockUseSearchState = vi.hoisted(() => ({
  state: {
    mutate: vi.fn(),
    isPending: false,
    data: null as {
      results: Array<{
        id: string
        title: string
        parent_id: unknown
        final_score: number
        created: string
        updated: string
      }>
      total_count: number
      search_type: string
    } | null,
  },
}))

const mockUseAskState = vi.hoisted(() => ({
  state: {
    isStreaming: false,
    strategy: null,
    answers: [] as string[],
    finalAnswer: null as string | null,
    sendAsk: vi.fn(),
  },
}))

vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
    prefetch: vi.fn(),
  }),
  usePathname: () => '',
  useSearchParams: () => new URLSearchParams(mockSearchParamsState.value),
}))

vi.mock('@/lib/hooks/use-search', () => ({
  useSearch: () => mockUseSearchState.state,
}))

vi.mock('@/lib/hooks/use-ask', () => ({
  useAsk: () => mockUseAskState.state,
}))

vi.mock('@/lib/hooks/use-models', () => ({
  useModelDefaults: () => ({
    data: {
      default_embedding_model: 'model:embedding',
      default_chat_model: 'model:chat',
      default_tools_model: 'model:tools',
    },
    isLoading: false,
  }),
  useModels: () => ({
    data: [
      { id: 'model:tools', name: 'Tools Model' },
      { id: 'model:chat', name: 'Chat Model' },
    ],
  }),
}))

vi.mock('@/lib/hooks/use-modal-manager', () => ({
  useModalManager: () => ({
    openModal: mockOpenModal,
  }),
}))

const mockOpenModal = vi.hoisted(() => vi.fn())

vi.mock('@/components/search/AdvancedModelsDialog', () => ({
  AdvancedModelsDialog: () => null,
}))

vi.mock('@/components/search/SaveToNotebooksDialog', () => ({
  SaveToNotebooksDialog: () => null,
}))

describe('SearchPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockSearchParamsState.value = ''
    mockUseSearchState.state.data = null
    mockUseSearchState.state.isPending = false
    mockUseAskState.state.isStreaming = false
    mockUseAskState.state.strategy = null
    mockUseAskState.state.answers = []
    mockUseAskState.state.finalAnswer = null
  })

  it('uses knowledge explorer naming and removes beta labels', () => {
    render(<SearchPage />)

    expect(screen.getByRole('heading', { name: 'Knowledge Explorer' })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: 'Ask' })).toBeInTheDocument()
    expect(screen.getByText('Ask Your Knowledge Base')).toBeInTheDocument()
    expect(screen.queryByText(/beta/i)).not.toBeInTheDocument()
  })

  it('owns dashboard scrolling so long answers can reach the bottom', () => {
    const { container } = render(<SearchPage />)

    expect(container.firstElementChild).toHaveClass('flex-1', 'overflow-y-auto')
  })

  it('keeps ask actions inside the card when a save action appears', () => {
    mockUseAskState.state.finalAnswer = 'A final answer'

    render(<SearchPage />)

    expect(screen.getByRole('button', { name: 'Ask' })).toHaveClass('sm:w-auto', 'sm:flex-1')
    expect(screen.getByRole('button', { name: 'Save to Notebooks' })).toHaveClass('sm:w-auto', 'sm:flex-1')
  })

  it('renders search results with object-shaped parent ids', () => {
    mockUseSearchState.state.data = {
      total_count: 1,
      search_type: 'text',
      results: [
        {
          id: 'search_result:bsd',
          title: 'BSD source',
          parent_id: { tb: 'source', id: 'bsd_source' },
          final_score: 0.91,
          matches: ['## Matched Heading\n\nPlain **body** text.\n\n![diagram](images/example.png)'],
          created: '2026-05-07T00:00:00Z',
          updated: '2026-05-07T00:00:00Z',
        },
      ],
    }
    mockSearchParamsState.value = 'mode=search'

    render(<SearchPage />)

    fireEvent.click(screen.getByRole('button', { name: 'BSD source' }))

    expect(screen.getByText('1 results found')).toBeInTheDocument()
    expect(mockOpenModal).toHaveBeenCalledWith('source', 'bsd_source')
  })

  it('renders expanded search matches as markdown', () => {
    mockUseSearchState.state.data = {
      total_count: 1,
      search_type: 'vector',
      results: [
        {
          id: 'search_result:bsd',
          title: 'BSD source',
          parent_id: 'source:bsd_source',
          final_score: 0.91,
          matches: ['## Matched Heading\n\nPlain **body** text.\n\n![diagram](images/example.png)'],
          created: '2026-05-07T00:00:00Z',
          updated: '2026-05-07T00:00:00Z',
        },
      ],
    }
    mockSearchParamsState.value = 'mode=search'

    render(<SearchPage />)

    fireEvent.click(screen.getByRole('button', { name: 'Matches (1)' }))

    expect(screen.getByRole('heading', { name: 'Matched Heading' })).toBeInTheDocument()
    expect(screen.getByText('body').tagName).toBe('STRONG')
    expect(screen.queryByAltText('diagram')).not.toBeInTheDocument()
  })
})
