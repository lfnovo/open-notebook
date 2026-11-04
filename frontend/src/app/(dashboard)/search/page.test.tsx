import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import SearchPage from './page'
import { useSearch } from '@/lib/hooks/use-search'
import { useModalManager } from '@/lib/hooks/use-modal-manager'
import { useModelDefaults } from '@/lib/hooks/use-models'

const { sendAsk, urlParams } = vi.hoisted(() => ({
  sendAsk: vi.fn(),
  urlParams: { value: 'mode=search' },
}))

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn() }),
  usePathname: () => '/search',
  useSearchParams: () => new URLSearchParams(urlParams.value),
}))

vi.mock('@/components/layout/AppShell', () => ({
  AppShell: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}))

vi.mock('@/components/search/NotebookScopeSelector', () => ({
  NotebookScopeSelector: () => null,
}))

vi.mock('@/components/search/StreamingResponse', () => ({
  StreamingResponse: () => null,
}))

// Stands in for the dialog: exposes its initial values and a button that saves custom models
vi.mock('@/components/search/AdvancedModelsDialog', () => ({
  AdvancedModelsDialog: ({
    defaultModels,
    onSave,
  }: {
    defaultModels: { strategy: string; answer: string; finalAnswer: string }
    onSave: (models: { strategy: string; answer: string; finalAnswer: string }) => void
  }) => (
    <div>
      <span data-testid="advanced-defaults">{JSON.stringify(defaultModels)}</span>
      <button
        onClick={() => onSave({ strategy: 'model:custom-s', answer: 'model:custom-a', finalAnswer: 'model:custom-f' })}
      >
        save custom models
      </button>
    </div>
  ),
}))

vi.mock('@/components/search/SaveToNotebooksDialog', () => ({
  SaveToNotebooksDialog: () => null,
}))

vi.mock('@/lib/hooks/use-search', () => ({
  useSearch: vi.fn(),
}))

vi.mock('@/lib/hooks/use-ask', () => ({
  useAsk: () => ({
    sendAsk,
    isStreaming: false,
    strategy: null,
    answers: [],
    finalAnswer: '',
  }),
}))

vi.mock('@/lib/hooks/use-models', () => ({
  useModelDefaults: vi.fn(),
  useModels: () => ({
    data: [
      { id: 'model:chat', name: 'chat-model' },
      { id: 'model:tools', name: 'tools-model' },
    ],
    isLoading: false,
  }),
}))

vi.mock('@/lib/hooks/use-modal-manager', () => ({
  useModalManager: vi.fn(),
}))

const mockUseSearch = vi.mocked(useSearch)
const mockUseModalManager = vi.mocked(useModalManager)
const mockUseModelDefaults = vi.mocked(useModelDefaults)
const openModal = vi.fn()

function mockModelDefaults(defaults: { default_chat_model: string; default_tools_model?: string | null }) {
  mockUseModelDefaults.mockReturnValue({
    data: { default_embedding_model: 'model:embedding', ...defaults },
    isLoading: false,
  } as unknown as ReturnType<typeof useModelDefaults>)
}

function askQuestion() {
  fireEvent.change(screen.getByRole('textbox'), { target: { value: 'What is new?' } })
  fireEvent.click(screen.getByRole('button', { name: 'searchPage.ask' }))
}

describe('SearchPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    urlParams.value = 'mode=search'
    mockUseModelDefaults.mockReturnValue({ data: null, isLoading: false } as unknown as ReturnType<typeof useModelDefaults>)
    mockUseSearch.mockReturnValue({
      data: {
        results: [{
          id: 'source_insight:matched-insight',
          parent_id: 'source:parent-source',
          title: 'Matched insight',
          final_score: 0.9,
          created: '2026-01-01T00:00:00Z',
          updated: '2026-01-01T00:00:00Z',
        }],
        total_count: 1,
        search_type: 'text',
      },
      isPending: false,
      mutate: vi.fn(),
    } as unknown as ReturnType<typeof useSearch>)
    mockUseModalManager.mockReturnValue({ openModal } as unknown as ReturnType<typeof useModalManager>)
  })

  it('opens the record that matched instead of its parent source', () => {
    render(<SearchPage />)

    fireEvent.click(screen.getByRole('button', { name: 'Matched insight' }))

    expect(openModal).toHaveBeenCalledWith('insight', 'matched-insight')
  })

  describe('Ask default models', () => {
    beforeEach(() => {
      urlParams.value = 'mode=ask'
    })

    it('uses the tools model for every stage when one is set', () => {
      mockModelDefaults({ default_chat_model: 'model:chat', default_tools_model: 'model:tools' })
      render(<SearchPage />)

      askQuestion()

      expect(sendAsk).toHaveBeenCalledWith(
        'What is new?',
        { strategy: 'model:tools', answer: 'model:tools', finalAnswer: 'model:tools' },
        { notebookIds: [] }
      )
      expect(screen.getByText('searchPage.strategy: tools-model')).toBeInTheDocument()
      expect(screen.getByText('searchPage.answer: tools-model')).toBeInTheDocument()
      expect(screen.getByText('searchPage.final: tools-model')).toBeInTheDocument()
      expect(JSON.parse(screen.getByTestId('advanced-defaults').textContent ?? '')).toEqual({
        strategy: 'model:tools',
        answer: 'model:tools',
        finalAnswer: 'model:tools',
      })
    })

    it('falls back to the chat model when no tools model is set', () => {
      mockModelDefaults({ default_chat_model: 'model:chat', default_tools_model: null })
      render(<SearchPage />)

      askQuestion()

      expect(sendAsk).toHaveBeenCalledWith(
        'What is new?',
        { strategy: 'model:chat', answer: 'model:chat', finalAnswer: 'model:chat' },
        { notebookIds: [] }
      )
      expect(screen.getByText('searchPage.strategy: chat-model')).toBeInTheDocument()
    })

    it('lets models picked in Advanced override the defaults', () => {
      mockModelDefaults({ default_chat_model: 'model:chat', default_tools_model: 'model:tools' })
      render(<SearchPage />)

      fireEvent.click(screen.getByRole('button', { name: 'save custom models' }))
      askQuestion()

      expect(sendAsk).toHaveBeenCalledWith(
        'What is new?',
        { strategy: 'model:custom-s', answer: 'model:custom-a', finalAnswer: 'model:custom-f' },
        { notebookIds: [] }
      )
    })
  })
})
