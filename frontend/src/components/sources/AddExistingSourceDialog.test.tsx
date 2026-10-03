import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { AddExistingSourceDialog } from './AddExistingSourceDialog'
import { searchApi } from '@/lib/api/search'
import { sourcesApi } from '@/lib/api/sources'

vi.mock('use-debounce', () => ({
  useDebounce: (value: string) => [value],
}))

vi.mock('@/lib/api/search', () => ({
  searchApi: { search: vi.fn() },
}))

vi.mock('@/lib/api/sources', () => ({
  sourcesApi: { list: vi.fn() },
}))

const mutateAsync = vi.fn()
vi.mock('@/lib/hooks/use-sources', () => ({
  useSources: () => ({ data: [] }),
  useAddSourcesToNotebook: () => ({ mutateAsync, isPending: false }),
}))

const mockSearch = vi.mocked(searchApi.search)
const mockList = vi.mocked(sourcesApi.list)

describe('AddExistingSourceDialog', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockList.mockResolvedValue([])
    mockSearch.mockResolvedValue({
      results: [
        {
          id: 'source:shared',
          parent_id: 'source:shared',
          title: 'Direct source match',
          final_score: 0.9,
          created: '2026-01-01T00:00:00Z',
          updated: '2026-01-01T00:00:00Z',
        },
        {
          id: 'source_insight:child',
          parent_id: 'source:shared',
          title: 'Insight from same source',
          final_score: 0.8,
          created: '2026-01-01T00:00:00Z',
          updated: '2026-01-01T00:00:00Z',
        },
      ],
      total_count: 2,
      search_type: 'text',
    })
  })

  it('shows a source only once when several search hits have the same parent', async () => {
    render(
      <AddExistingSourceDialog
        open={true}
        onOpenChange={vi.fn()}
        notebookId="notebook:1"
      />
    )

    fireEvent.change(screen.getByPlaceholderText('sources.searchPlaceholder'), {
      target: { value: 'shared' },
    })

    await waitFor(() => expect(mockSearch).toHaveBeenCalled())
    expect(screen.getByText('Direct source match')).toBeInTheDocument()
    expect(screen.queryByText('Insight from same source')).not.toBeInTheDocument()
  })
})
