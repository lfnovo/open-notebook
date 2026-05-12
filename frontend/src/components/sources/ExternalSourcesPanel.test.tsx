import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { ExternalSourcesPanel } from './ExternalSourcesPanel'

const fetchMutate = vi.fn()
const snapshotMutate = vi.fn()
const searchMutate = vi.fn()
let fetchCommandStatus = 'running'
let availableSourcesState = {
  data: {
    items: [
      {
        id: 'external_source:papers',
        name: 'Paper Search',
        monthly_request_quota: 100,
        current_month_usage: 12,
      },
    ],
  },
  isFetching: false,
  isLoading: false,
}

vi.mock('@/lib/hooks/use-workspaces', () => ({
  useCurrentWorkspace: () => ({
    currentWorkspace: {
      id: 'workspace:team',
      type: 'team',
      team_id: 'team:research',
    },
  }),
}))

vi.mock('@/lib/hooks/use-external-api', () => ({
  useAvailableExternalSources: () => availableSourcesState,
  useSearchExternalSource: () => ({
    mutateAsync: searchMutate,
    isPending: false,
  }),
  useFetchExternalItem: () => ({
    mutateAsync: fetchMutate,
    isPending: false,
  }),
  useReferenceExternalItem: () => ({
    mutateAsync: vi.fn(),
    isPending: false,
  }),
  useSnapshotExternalItem: () => ({
    mutateAsync: snapshotMutate,
    isPending: false,
  }),
  useExternalApiCommand: (commandId?: string | null) => ({
    data: commandId === 'command:fetch'
      ? {
        status: fetchCommandStatus,
        result: fetchCommandStatus === 'completed'
          ? {
            items: [
              {
                id: 'external_source_item:fetched_paper',
                source_id: 'external_source:papers',
                team_id: 'team:research',
                external_id: 'paper:one',
                title: 'Paper One',
                summary: 'A paper result.',
                content_markdown: '# Paper One',
                authors: [],
                metadata: {},
                created: '2026-05-11T00:00:00Z',
                updated: '2026-05-11T00:00:00Z',
              },
            ],
          }
          : null,
      }
      : commandId === 'command:search'
        ? {
          status: 'completed',
          result: {
            items: [
              {
                id: 'external_source_item:paper',
                source_id: 'external_source:papers',
                team_id: 'team:research',
                external_id: 'paper:one',
                title: 'Paper One',
                summary: 'A paper result.',
                authors: [],
                metadata: {},
                created: '2026-05-11T00:00:00Z',
                updated: '2026-05-11T00:00:00Z',
              },
            ],
          },
        }
        : undefined,
    isLoading: false,
  }),
}))

function renderPanel() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })
  const ui = () => (
    <QueryClientProvider client={queryClient}>
      <ExternalSourcesPanel notebookId="notebook:one" canCreateSource />
    </QueryClientProvider>
  )
  const view = render(ui())
  return { ...view, rerenderPanel: () => view.rerender(ui()) }
}

describe('ExternalSourcesPanel', () => {
  beforeEach(() => {
    fetchMutate.mockReset()
    snapshotMutate.mockReset()
    searchMutate.mockReset()
    fetchCommandStatus = 'running'
    availableSourcesState = {
      data: {
        items: [
          {
            id: 'external_source:papers',
            name: 'Paper Search',
            monthly_request_quota: 100,
            current_month_usage: 12,
          },
        ],
      },
      isFetching: false,
      isLoading: false,
    }
    searchMutate.mockResolvedValue({ command_id: 'command:search' })
    fetchMutate.mockResolvedValue({ command_id: 'command:fetch' })
    snapshotMutate.mockResolvedValue({})
  })

  it('keeps the empty authorized-source state hidden while sources are loading', () => {
    availableSourcesState = {
      data: undefined,
      isFetching: true,
      isLoading: true,
    }

    const { container } = renderPanel()

    expect(screen.queryByText('No external sources are authorized for this team.')).not.toBeInTheDocument()
    expect(container.querySelector('.animate-spin')).toBeInTheDocument()
  })

  it('shows source selector and quota on one row without an external api heading', () => {
    const { container } = renderPanel()

    expect(screen.queryByRole('heading', { name: 'External APIs' })).not.toBeInTheDocument()
    expect(screen.getByText('Quota 12/100 this month')).toBeInTheDocument()
    expect(screen.getByText('Paper Search')).toBeInTheDocument()
    expect(container.querySelector('[data-testid="external-source-selector-row"]')).toHaveClass('sm:flex-row')
  })

  it('shows one join action for external results and fetches before importing', async () => {
    renderPanel()

    fireEvent.change(screen.getByPlaceholderText('Search external source'), {
      target: { value: 'paper' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Search external source' }))

    await screen.findByText('Paper One')
    expect(screen.getByText('Paper One')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Fetch' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Ref' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Snapshot' })).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Join' }))

    await waitFor(() => expect(fetchMutate).toHaveBeenCalledWith({
      itemId: 'external_source_item:paper',
      teamId: 'team:research',
    }))
    expect(snapshotMutate).not.toHaveBeenCalled()
  })

  it('snapshots a fetched item only once when the completed command re-renders', async () => {
    const view = renderPanel()

    fireEvent.change(screen.getByPlaceholderText('Search external source'), {
      target: { value: 'paper' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Search external source' }))
    await screen.findByText('Paper One')
    fireEvent.click(screen.getByRole('button', { name: 'Join' }))

    await waitFor(() => expect(fetchMutate).toHaveBeenCalled())

    fetchCommandStatus = 'completed'
    view.rerenderPanel()
    await waitFor(() => expect(snapshotMutate).toHaveBeenCalledTimes(1))

    view.rerenderPanel()
    expect(snapshotMutate).toHaveBeenCalledTimes(1)
  })
})
