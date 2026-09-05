/* eslint-disable @typescript-eslint/no-explicit-any */
import { StrictMode } from 'react'
import { renderHook, act } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { useAsk } from './use-ask'
import { searchApi } from '@/lib/api/search'

vi.mock('@/lib/api/search', () => ({
  searchApi: { askKnowledgeBase: vi.fn() },
}))

vi.mock('sonner', () => ({
  toast: { error: vi.fn(), success: vi.fn() },
}))

const MODELS = {
  strategy: 'model:strategy',
  answer: 'model:answer',
  finalAnswer: 'model:final',
}

// Build a ReadableStream of SSE frames shaped like the backend's
// `data: {json}\n\n` output (api/routers/search.py stream_ask_response).
function sseStream(events: Array<Record<string, unknown>>) {
  const encoder = new TextEncoder()
  return new ReadableStream<Uint8Array>({
    start(controller) {
      for (const event of events) {
        controller.enqueue(encoder.encode(`data: ${JSON.stringify(event)}\n\n`))
      }
      controller.close()
    },
  })
}

// Regression coverage for the mountedRef guard. StrictMode mounts, unmounts and
// remounts, which is exactly the sequence that used to leave mountedRef.current
// false forever and turn every state update in this hook into a no-op. These
// assertions fail without the `mountedRef.current = true` setup assignment.
describe('useAsk under React StrictMode', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('clears the loading state and exposes the answer when the stream completes', async () => {
    vi.mocked(searchApi.askKnowledgeBase).mockResolvedValue(
      sseStream([
        { type: 'strategy', reasoning: 'because', searches: [{ term: 't', instructions: 'i' }] },
        { type: 'answer', content: 'partial answer' },
        { type: 'final_answer', content: 'the final answer' },
        { type: 'complete', final_answer: 'the final answer' },
      ]) as any
    )

    const { result } = renderHook(() => useAsk(), { wrapper: StrictMode })

    await act(async () => {
      await result.current.sendAsk('why?', MODELS)
    })

    expect(result.current.isStreaming).toBe(false)
    expect(result.current.finalAnswer).toBe('the final answer')
    expect(result.current.strategy?.searches).toHaveLength(1)
    expect(result.current.answers).toEqual(['partial answer'])
  })

  it('surfaces an in-band error event instead of loading forever', async () => {
    vi.mocked(searchApi.askKnowledgeBase).mockResolvedValue(
      sseStream([
        { type: 'strategy', reasoning: 'because', searches: [] },
        { type: 'error', message: 'The AI provider is temporarily unavailable.' },
      ]) as any
    )

    const { result } = renderHook(() => useAsk(), { wrapper: StrictMode })

    await act(async () => {
      await result.current.sendAsk('why?', MODELS)
    })

    expect(result.current.isStreaming).toBe(false)
    expect(result.current.error).toBe('The AI provider is temporarily unavailable.')
  })
})

describe('useAsk notebook scope (#574, #87)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('sends notebook_ids when a scope is given', async () => {
    vi.mocked(searchApi.askKnowledgeBase).mockResolvedValue(
      sseStream([{ type: 'complete', final_answer: 'a' }]) as any
    )
    const { result } = renderHook(() => useAsk())

    await act(async () => {
      await result.current.sendAsk('why?', MODELS, { notebookIds: ['notebook:a'] })
    })

    expect(vi.mocked(searchApi.askKnowledgeBase).mock.calls[0][0]).toMatchObject({
      question: 'why?',
      notebook_ids: ['notebook:a'],
    })
  })

  it('omits notebook_ids for a global ask', async () => {
    vi.mocked(searchApi.askKnowledgeBase).mockResolvedValue(
      sseStream([{ type: 'complete', final_answer: 'a' }]) as any
    )
    const { result } = renderHook(() => useAsk())

    await act(async () => {
      await result.current.sendAsk('why?', MODELS, { notebookIds: [] })
    })

    expect(vi.mocked(searchApi.askKnowledgeBase).mock.calls[0][0]).not.toHaveProperty('notebook_ids')
  })
})
