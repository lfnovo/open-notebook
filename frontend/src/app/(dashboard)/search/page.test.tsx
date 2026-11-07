import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useSearchParams } from 'next/navigation'
import SearchPage from './page'
import { useSearch } from '@/lib/hooks/use-search'
import { useModalManager } from '@/lib/hooks/use-modal-manager'
import { useModelDefaults } from '@/lib/hooks/use-models'
import { useAsk } from '@/lib/hooks/use-ask'

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn() }),
  usePathname: () => '/search',
  useSearchParams: vi.fn(),
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

vi.mock('@/components/search/AdvancedModelsDialog', () => ({
  AdvancedModelsDialog: () => null,
}))

vi.mock('@/components/search/SaveToNotebooksDialog', () => ({
  SaveToNotebooksDialog: () => null,
}))

vi.mock('@/lib/hooks/use-search', () => ({
  useSearch: vi.fn(),
}))

vi.mock('@/lib/hooks/use-ask', () => ({
  useAsk: vi.fn(),
}))

vi.mock('@/lib/hooks/use-models', () => ({
  useModelDefaults: vi.fn(),
  useModels: () => ({ data: [], isLoading: false }),
}))

vi.mock('@/lib/hooks/use-modal-manager', () => ({
  useModalManager: vi.fn(),
}))

const mockUseSearch = vi.mocked(useSearch)
const mockUseModalManager = vi.mocked(useModalManager)
const mockUseModelDefaults = vi.mocked(useModelDefaults)
const mockUseSearchParams = vi.mocked(useSearchParams)
const mockUseAsk = vi.mocked(useAsk)
const openModal = vi.fn()
const sendAsk = vi.fn()

describe('SearchPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockUseSearchParams.mockReturnValue(
      new URLSearchParams('mode=search') as ReturnType<typeof useSearchParams>,
    )
    mockUseModelDefaults.mockReturnValue({
      data: undefined,
      isLoading: false,
    } as ReturnType<typeof useModelDefaults>)
    mockUseAsk.mockReturnValue({
      sendAsk,
      isStreaming: false,
      strategy: null,
      answers: [],
      finalAnswer: null,
      error: null,
      reset: vi.fn(),
    })
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

  it.each([undefined, null, 'model:embedding'])(
    'shows the Ask shortcut hint only with an embedding model (%s)',
    (embeddingModel) => {
      mockUseSearchParams.mockReturnValue(
        new URLSearchParams('mode=ask') as ReturnType<typeof useSearchParams>,
      )
      mockUseModelDefaults.mockReturnValue({
        data: {
          default_chat_model: 'model:chat',
          default_embedding_model: embeddingModel,
        },
        isLoading: false,
      } as ReturnType<typeof useModelDefaults>)

      render(<SearchPage />)

      if (embeddingModel) {
        expect(screen.getByText('searchPage.pressToSubmit')).toBeInTheDocument()
        expect(screen.queryByText('searchPage.noEmbeddingModel')).not.toBeInTheDocument()
      } else {
        expect(screen.queryByText('searchPage.pressToSubmit')).not.toBeInTheDocument()
        expect(screen.getByText('searchPage.noEmbeddingModel')).toBeInTheDocument()
      }
    },
  )

  describe.each([
    { name: 'Ctrl+Enter', modifiers: { ctrlKey: true } },
    { name: 'Cmd+Enter', modifiers: { metaKey: true } },
  ])('$name', ({ modifiers }) => {
    it.each([undefined, null, '', 'model:embedding'])(
      'submits only with an embedding model (%s)',
      (embeddingModel) => {
        mockUseSearchParams.mockReturnValue(
          new URLSearchParams('mode=ask') as ReturnType<typeof useSearchParams>,
        )
        mockUseModelDefaults.mockReturnValue({
          data: {
            default_chat_model: 'model:chat',
            default_embedding_model: embeddingModel,
          },
          isLoading: false,
        } as ReturnType<typeof useModelDefaults>)

        render(<SearchPage />)

        const question = 'What is in this notebook?'
        const input = screen.getByRole('textbox', { name: 'common.accessibility.enterQuestion' })
        fireEvent.change(input, { target: { value: question } })
        fireEvent.keyDown(input, { key: 'Enter', ...modifiers })

        if (embeddingModel) {
          expect(sendAsk).toHaveBeenCalledTimes(1)
          expect(sendAsk).toHaveBeenCalledWith(
            question,
            { strategy: 'model:chat', answer: 'model:chat', finalAnswer: 'model:chat' },
            { notebookIds: [] },
          )
        } else {
          expect(sendAsk).not.toHaveBeenCalled()
        }
      },
    )
  })
})
