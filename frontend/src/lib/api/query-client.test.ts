import { MutationObserver } from '@tanstack/react-query'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { NotebookResponse } from '@/lib/types/api'
import { queryClient } from './query-client'
import { notebooksApi } from './notebooks'

vi.mock('./notebooks', () => ({
  notebooksApi: { create: vi.fn(), get: vi.fn() },
}))

const notebook: NotebookResponse = {
  id: 'notebook:1', name: 'Research', description: '', archived: false,
  created: '2026-01-01', updated: '2026-01-01',
  source_count: 0, note_count: 0,
}
const input = { name: notebook.name }
const httpError = (status: number) => Object.assign(new Error(`HTTP ${status}`), {
  isAxiosError: true,
  response: { status },
})

afterEach(() => {
  queryClient.clear()
  vi.resetAllMocks()
})

describe('shared query client retry policy', () => {
  // #1395: a failed write may already have taken effect on the server.
  it.each([
    ['a gateway error', httpError(502)],
    ['a lost response', new Error('Network Error')],
    ['a validation error', httpError(422)],
  ])('does not repeat a mutation after %s', async (_, error) => {
    vi.mocked(notebooksApi.create).mockRejectedValue(error)
    const mutation = new MutationObserver(queryClient, {
      mutationFn: () => notebooksApi.create(input),
    })

    await expect(mutation.mutate()).rejects.toBe(error)

    expect(notebooksApi.create).toHaveBeenCalledExactlyOnceWith(input)
  })

  it('returns a successful mutation without repeating it', async () => {
    vi.mocked(notebooksApi.create).mockResolvedValue(notebook)
    const mutation = new MutationObserver(queryClient, {
      mutationFn: () => notebooksApi.create(input),
    })

    await expect(mutation.mutate()).resolves.toEqual(notebook)
    expect(notebooksApi.create).toHaveBeenCalledExactlyOnceWith(input)
  })

  it('allows the caller to submit again after a failed mutation', async () => {
    const error = httpError(502)
    vi.mocked(notebooksApi.create).mockRejectedValue(error)
    const mutation = new MutationObserver(queryClient, {
      mutationFn: () => notebooksApi.create(input),
    })
    await expect(mutation.mutate()).rejects.toBe(error)
    expect(notebooksApi.create).toHaveBeenCalledTimes(1)

    vi.mocked(notebooksApi.create).mockResolvedValue(notebook)
    await expect(mutation.mutate()).resolves.toEqual(notebook)
    expect(notebooksApi.create).toHaveBeenCalledTimes(2)
  })

  it('preserves an explicit caller retry policy', async () => {
    vi.mocked(notebooksApi.create)
      .mockRejectedValueOnce(httpError(502))
      .mockResolvedValue(notebook)
    const mutation = new MutationObserver(queryClient, {
      mutationFn: () => notebooksApi.create(input),
      retry: 1,
      retryDelay: 0,
    })

    await expect(mutation.mutate()).resolves.toEqual(notebook)
    expect(notebooksApi.create).toHaveBeenCalledTimes(2)
  })

  it('still retries a transient read failure', async () => {
    vi.mocked(notebooksApi.get)
      .mockRejectedValueOnce(httpError(503))
      .mockRejectedValueOnce(httpError(503))
      .mockResolvedValue(notebook)

    await expect(queryClient.fetchQuery({
      queryKey: ['notebooks', notebook.id],
      queryFn: () => notebooksApi.get(notebook.id),
      retryDelay: 0,
    })).resolves.toEqual(notebook)
    expect(notebooksApi.get).toHaveBeenCalledTimes(3)
  })

  it('does not retry a missing item read', async () => {
    const error = httpError(404)
    vi.mocked(notebooksApi.get).mockRejectedValue(error)

    await expect(queryClient.fetchQuery({
      queryKey: ['notebooks', notebook.id],
      queryFn: () => notebooksApi.get(notebook.id),
      retryDelay: 0,
    })).rejects.toBe(error)
    expect(notebooksApi.get).toHaveBeenCalledExactlyOnceWith(notebook.id)
  })
})
