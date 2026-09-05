/* eslint-disable @typescript-eslint/no-explicit-any */
import type { ReactNode } from 'react'
import { renderHook, act, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { useSourceChat } from './use-source-chat'
import { sourceChatApi } from '@/lib/api/source-chat'
import { SourceChatSession } from '@/lib/types/api'

// useTranslation is mocked globally in setup.ts (t returns the key string).

vi.mock('@/lib/api/source-chat', () => ({
  sourceChatApi: {
    listSessions: vi.fn(),
    getSession: vi.fn(),
    createSession: vi.fn(),
    updateSession: vi.fn(),
    deleteSession: vi.fn(),
    sendMessage: vi.fn(),
  },
}))

vi.mock('sonner', () => ({
  toast: { error: vi.fn(), success: vi.fn() },
}))

const session: SourceChatSession = {
  id: 'session:1',
  title: 'My Chat',
  source_id: 'source:1',
  created: '2026-01-01T00:00:00Z',
  updated: '2026-01-02T00:00:00Z',
  model_override: null,
}

// Build a ReadableStream of SSE frames shaped like the backend's
// `data: {json}\n\n` output (api/routers/source_chat.py).
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

// A fresh QueryClient per test, kept stable across renders (creating it inside
// the wrapper body would reset cached queries on every hook re-render).
function makeWrapper() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>
  }
}

describe('useSourceChat sendMessage streaming', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('streams a message with a message_id and an AbortSignal, then resets state and refetches', async () => {
    vi.mocked(sourceChatApi.listSessions).mockResolvedValue([session])
    vi.mocked(sourceChatApi.getSession).mockResolvedValue({ ...session, messages: [] })
    vi.mocked(sourceChatApi.sendMessage).mockResolvedValue(
      sseStream([
        { type: 'ai_message', content: 'hi' },
        { type: 'complete' },
      ]) as any
    )

    const { result } = renderHook(() => useSourceChat('source:1'), { wrapper: makeWrapper() })

    await waitFor(() => expect(result.current.currentSessionId).toBe('session:1'))
    await waitFor(() => expect(sourceChatApi.getSession).toHaveBeenCalled())
    const refetchesBefore = vi.mocked(sourceChatApi.getSession).mock.calls.length

    await act(async () => {
      await result.current.sendMessage('hello')
    })

    // The AbortController path: sendMessage got a client message_id and a signal.
    const [, , payload, signal] = vi.mocked(sourceChatApi.sendMessage).mock.calls[0]
    expect(payload.message_id).toBeTruthy()
    expect(payload.message).toBe('hello')
    expect(signal).toBeInstanceOf(AbortSignal)

    // Stream finished -> isStreaming cleared and the session was refetched.
    expect(result.current.isStreaming).toBe(false)
    await waitFor(() =>
      expect(vi.mocked(sourceChatApi.getSession).mock.calls.length).toBeGreaterThan(refetchesBefore)
    )
  })

  it('reuses the trailing unanswered human id on a retry of the same content', async () => {
    vi.mocked(sourceChatApi.listSessions).mockResolvedValue([session])
    vi.mocked(sourceChatApi.getSession).mockResolvedValue({
      ...session,
      messages: [
        { id: 'msg-persisted', type: 'human', content: 'hello', timestamp: '2026-01-01T00:00:00Z' },
      ],
    })
    vi.mocked(sourceChatApi.sendMessage).mockResolvedValue(sseStream([{ type: 'complete' }]) as any)

    const { result } = renderHook(() => useSourceChat('source:1'), { wrapper: makeWrapper() })

    // Wait for the persisted trailing human message to be loaded into state.
    await waitFor(() => expect(result.current.messages).toHaveLength(1))

    await act(async () => {
      await result.current.sendMessage('hello')
    })

    const [, , payload] = vi.mocked(sourceChatApi.sendMessage).mock.calls[0]
    expect(payload.message_id).toBe('msg-persisted')
  })

  it('cancels an in-flight stream, aborting its signal and clearing isStreaming', async () => {
    vi.mocked(sourceChatApi.listSessions).mockResolvedValue([session])
    vi.mocked(sourceChatApi.getSession).mockResolvedValue({ ...session, messages: [] })
    // Never settles: the stream stays in-flight until the user cancels.
    vi.mocked(sourceChatApi.sendMessage).mockImplementation(() => new Promise(() => {}))

    const { result } = renderHook(() => useSourceChat('source:1'), { wrapper: makeWrapper() })

    await waitFor(() => expect(result.current.currentSessionId).toBe('session:1'))

    let sendPromise: Promise<void>
    act(() => {
      sendPromise = result.current.sendMessage('hello')
    })

    await waitFor(() => expect(result.current.isStreaming).toBe(true))

    const signal = vi.mocked(sourceChatApi.sendMessage).mock.calls[0][3] as AbortSignal
    expect(signal.aborted).toBe(false)

    act(() => {
      result.current.cancelStreaming()
    })

    expect(signal.aborted).toBe(true)
    expect(result.current.isStreaming).toBe(false)

    // Clean up the dangling promise so the test doesn't leak a pending microtask.
    void sendPromise
  })

  it('a failed session auto-create leaves isStreaming false', async () => {
    vi.mocked(sourceChatApi.listSessions).mockResolvedValue([])
    vi.mocked(sourceChatApi.createSession).mockRejectedValue(new Error('boom'))

    const { result } = renderHook(() => useSourceChat('source:1'), { wrapper: makeWrapper() })

    await waitFor(() => expect(result.current.sessions).toEqual([]))

    await act(async () => {
      await result.current.sendMessage('hello')
    })

    expect(result.current.isStreaming).toBe(false)
    expect(sourceChatApi.sendMessage).not.toHaveBeenCalled()
  })
})
