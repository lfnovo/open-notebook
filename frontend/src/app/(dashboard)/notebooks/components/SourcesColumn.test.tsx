import { cleanup, fireEvent, render, renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import type { PropsWithChildren } from 'react'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { apiClient } from '@/lib/api/client'
import type { SourceListResponse } from '@/lib/types/api'
import { useNotebookChat } from '@/lib/hooks/use-notebook-chat'
import { computeSourceSelections } from '@/lib/utils/source-context'
import { SourcesColumn } from './SourcesColumn'

const source: SourceListResponse = {
  id: 'source:test',
  title: 'Test source',
  topics: [],
  asset: null,
  embedded: false,
  embedded_chunks: 0,
  insights_count: 0,
  created: '2026-10-19T00:00:00Z',
  updated: '2026-10-19T00:00:00Z',
  status: 'failed',
  command_id: 'command:test',
}
const completedStatus = { status: 'completed', message: 'Source processing completed' }
const fetchSourceStatus = vi.fn(() => completedStatus)
const originalAdapter = apiClient.defaults.adapter
const originalBaseURL = apiClient.defaults.baseURL
let client: QueryClient
let contextRequests: unknown[]

beforeEach(() => {
  fetchSourceStatus.mockReset().mockReturnValue(completedStatus)
  client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  contextRequests = []
  apiClient.defaults.baseURL = 'https://api.example.test/api'
  apiClient.defaults.adapter = async (config) => {
    if (config.url === '/chat/context') {
      contextRequests.push(JSON.parse(config.data))
    }
    return {
      data: config.url === '/chat/context'
        ? { context: { sources: [], notes: [] }, token_count: 0, char_count: 0 }
        : config.url?.endsWith('/status') ? fetchSourceStatus() : config.url === '/settings' ? {} : [],
      status: 200,
      statusText: 'OK',
      headers: {},
      config,
    }
  }
})

afterEach(() => {
  cleanup()
  client.clear()
  apiClient.defaults.adapter = originalAdapter
  apiClient.defaults.baseURL = originalBaseURL
})

function wrapper({ children }: PropsWithChildren) {
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>
}

it('keeps the context toggle off and usable before a source has a selection', () => {
  const onContextModeChange = vi.fn()
  const { container } = render(
    <SourcesColumn
      sources={[source]}
      isLoading={false}
      notebookId="notebook:test"
      contextSelections={{}}
      onContextModeChange={onContextModeChange}
    />,
    { wrapper },
  )
  const toggle = container.querySelector('svg.lucide-eye-off')?.closest('button')

  expect(toggle).toBeInTheDocument()
  fireEvent.click(toggle!)
  expect(onContextModeChange).toHaveBeenCalledWith(source.id, 'full')
})

it.each([
  { status: undefined, cached: false },
  { status: undefined, cached: true },
  { status: 'running', cached: true },
  { status: 'unknown', cached: false },
  { status: 'unknown', cached: true },
])('refreshes a source when its first status is completed ($status, cached=$cached)', async ({ status, cached }) => {
  if (cached) {
    client.setQueryData(['sources', source.id, 'status'], completedStatus)
  }
  const onRefresh = vi.fn()
  render(
    <SourcesColumn
      sources={[{ ...source, status }]}
      isLoading={false}
      notebookId="notebook:test"
      contextSelections={{}}
      onRefresh={onRefresh}
    />,
    { wrapper },
  )

  await waitFor(() => expect(onRefresh).toHaveBeenCalledTimes(1), { timeout: 2000 })
})

it.each([
  { status: 'completed', cached: false },
  { status: 'failed', cached: false },
  { status: 'completed', cached: true },
  { status: 'failed', cached: true },
])('polls an unknown source until $status and refreshes the list (cached=$cached, #1397)', async ({ status, cached }) => {
  if (cached) {
    client.setQueryData(['sources', source.id, 'status'], completedStatus)
  }
  fetchSourceStatus
    .mockReturnValueOnce({ status: 'unknown', message: 'Command status unavailable' })
    .mockReturnValue({ status, message: `Source processing ${status}` })
  const onRefresh = vi.fn(() => fetchSourceStatus.mock.results.at(-1)?.value.status)
  render(
    <SourcesColumn
      sources={[{ ...source, status: 'unknown' }]}
      isLoading={false}
      notebookId="notebook:test"
      contextSelections={{}}
      onRefresh={onRefresh}
    />,
    { wrapper },
  )

  await waitFor(() => expect(fetchSourceStatus).toHaveBeenCalledTimes(1))
  expect(onRefresh).not.toHaveBeenCalled()
  await waitFor(() => expect(onRefresh).toHaveReturnedWith(status), { timeout: 3500 })
  expect(fetchSourceStatus).toHaveBeenCalledTimes(2)
})

it('refreshes a failed source that completes immediately after retry', async () => {
  const onRefresh = vi.fn()
  const props = { isLoading: false, notebookId: 'notebook:test', onRefresh }
  const { rerender } = render(<SourcesColumn {...props} sources={[source]} />, { wrapper })
  client.setQueryData(['sources', source.id, 'status'], completedStatus)

  rerender(
    <SourcesColumn
      {...props}
      sources={[{ ...source, status: 'running', command_id: 'command:retry' }]}
    />,
  )

  await waitFor(() => expect(onRefresh).toHaveBeenCalledTimes(1), { timeout: 2000 })
})

it('sends an unready source as excluded and includes it after completion', async () => {
  const sources = [{ ...source, status: 'running' }]
  const selections = computeSourceSelections({}, sources)
  const notes: [] = []
  const { rerender } = renderHook(
    ({ sources, contextSelections }) => useNotebookChat({
      notebookId: 'notebook:test', sources, notes, contextSelections,
    }),
    { initialProps: { sources, contextSelections: { sources: selections, notes: {} } }, wrapper },
  )

  await waitFor(() => expect(contextRequests).toContainEqual({
    notebook_id: 'notebook:test',
    context_config: { sources: { 'source:test': 'not in' }, notes: {} },
  }))

  const completed = [{ ...source, status: 'completed' }]
  rerender({
    sources: completed,
    contextSelections: { sources: computeSourceSelections(selections, completed), notes: {} },
  })

  await waitFor(() => expect(contextRequests).toContainEqual({
    notebook_id: 'notebook:test',
    context_config: { sources: { 'source:test': 'full content' }, notes: {} },
  }))
})
