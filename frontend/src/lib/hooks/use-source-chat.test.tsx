/* eslint-disable @typescript-eslint/no-explicit-any */
import type { ReactNode } from 'react'
import { renderHook, act, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { toast } from 'sonner'
import { useSourceChat } from './use-source-chat'
import { sourceChatApi } from '@/lib/api/source-chat'
import { SourceChatSession, SourceChatSessionWithMessages, SourceChatMessage } from '@/lib/types/api'

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
function makeWrapper(
  client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
) {
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>
  }
}

// `fetch` rejects with an AbortError when its signal aborts — the mock has to do
// the same or a cancelled send never reaches its catch/finally.
function abortableSend() {
  return (
    _sourceId: string,
    _sessionId: string,
    _data: unknown,
    signal?: AbortSignal
  ) =>
    new Promise<never>((_resolve, reject) => {
      signal?.addEventListener('abort', () =>
        reject(new DOMException('Aborted', 'AbortError'))
      )
    })
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
    // Stays in-flight until the abort rejects it, like a real fetch would —
    // this is what lets the test observe the send's unwind.
    vi.mocked(sourceChatApi.sendMessage).mockImplementation(abortableSend() as any)

    const { result } = renderHook(() => useSourceChat('source:1'), { wrapper: makeWrapper() })

    await waitFor(() => expect(result.current.currentSessionId).toBe('session:1'))

    let sendPromise!: Promise<void>
    act(() => {
      sendPromise = result.current.sendMessage('hello')
    })

    await waitFor(() => expect(result.current.isStreaming).toBe(true))

    const signal = vi.mocked(sourceChatApi.sendMessage).mock.calls[0][3] as AbortSignal
    expect(signal.aborted).toBe(false)
    const refetchesBefore = vi.mocked(sourceChatApi.getSession).mock.calls.length

    act(() => {
      result.current.cancelStreaming()
    })

    expect(signal.aborted).toBe(true)
    expect(result.current.isStreaming).toBe(false)

    // Cancellation must actually unwind the send: the finally block refetches
    // the persisted checkpoint so the pending turn survives the cancel.
    await act(async () => {
      await sendPromise
    })
    await waitFor(() =>
      expect(vi.mocked(sourceChatApi.getSession).mock.calls.length).toBeGreaterThan(refetchesBefore)
    )
  })

  it('reuses the pending turn id when retrying immediately after a stop', async () => {
    // Stop frees the composer before the aborted send's reconciliation refetch
    // completes. The retry must still dedup against the server's pending turn:
    // the optimistic bubble carries the persisted id, so a same-content retry
    // reuses it instead of minting a fresh one the backend would append again.
    vi.mocked(sourceChatApi.listSessions).mockResolvedValue([session])
    let checkpoint: SourceChatMessage[] = []
    vi.mocked(sourceChatApi.getSession).mockImplementation(
      () => Promise.resolve({ ...session, messages: checkpoint }) as any
    )
    const firstSendImpl = abortableSend()
    vi.mocked(sourceChatApi.sendMessage).mockImplementation(((...args: any[]) => {
      const payload = args[2] as { message_id: string }
      if (vi.mocked(sourceChatApi.sendMessage).mock.calls.length === 1) {
        // The backend persists the turn as soon as the send starts.
        checkpoint = [
          {
            id: payload.message_id,
            type: 'human' as const,
            content: 'hello',
            timestamp: '2026-01-01T00:00:00Z',
          },
        ]
        return (firstSendImpl as (...a: any[]) => Promise<never>)(...args) as any
      }
      return Promise.resolve(sseStream([{ type: 'complete' }]) as any)
    }) as any)

    const { result } = renderHook(() => useSourceChat('source:1'), { wrapper: makeWrapper() })

    await waitFor(() => expect(result.current.currentSessionId).toBe('session:1'))

    let firstSend!: Promise<void>
    act(() => {
      firstSend = result.current.sendMessage('hello')
    })
    await waitFor(() => expect(result.current.isStreaming).toBe(true))
    await waitFor(() => expect(result.current.messages).toHaveLength(1))

    // Same tick as the stop: the reconciliation refetch has not run yet.
    let retry!: Promise<void>
    act(() => {
      result.current.cancelStreaming()
      retry = result.current.sendMessage('hello')
    })
    await act(async () => {
      await retry
    })
    void firstSend

    const calls = vi.mocked(sourceChatApi.sendMessage).mock.calls
    expect(calls).toHaveLength(2)
    expect(calls[1][2].message_id).toBe(calls[0][2].message_id)
    expect(result.current.messages).toHaveLength(1)
    expect(result.current.messages[0].id).toBe(calls[0][2].message_id)
  })

  it('fails the send when pre-send hydration errors instead of minting an unverified id', async () => {
    // The checkpoint may hold a pending turn the client cannot see — deriving
    // the id from an unverified list would mint a fresh one the backend keys
    // no dedup against, so the send must not go out.
    vi.mocked(sourceChatApi.listSessions).mockResolvedValue([session])
    vi.mocked(sourceChatApi.getSession).mockRejectedValue(new Error('network down'))

    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {})
    try {
      const { result } = renderHook(() => useSourceChat('source:1'), { wrapper: makeWrapper() })

      await waitFor(() => expect(result.current.currentSessionId).toBe('session:1'))

      await act(async () => {
        await result.current.sendMessage('hello')
      })

      expect(sourceChatApi.sendMessage).not.toHaveBeenCalled()
      expect(result.current.isStreaming).toBe(false)
      expect(toast.error).toHaveBeenCalled()
    } finally {
      consoleError.mockRestore()
    }
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

  it('does not append a duplicate optimistic bubble when retrying a pending turn', async () => {
    vi.mocked(sourceChatApi.listSessions).mockResolvedValue([session])
    vi.mocked(sourceChatApi.getSession).mockResolvedValue({
      ...session,
      messages: [
        { id: 'msg-persisted', type: 'human', content: 'hello', timestamp: '2026-01-01T00:00:00Z' },
      ],
    })
    vi.mocked(sourceChatApi.sendMessage).mockResolvedValue(sseStream([{ type: 'complete' }]) as any)

    const { result } = renderHook(() => useSourceChat('source:1'), { wrapper: makeWrapper() })

    await waitFor(() => expect(result.current.messages).toHaveLength(1))

    await act(async () => {
      await result.current.sendMessage('hello')
    })

    expect(result.current.messages).toHaveLength(1)
    expect(result.current.messages[0].id).toBe('msg-persisted')
  })

  it('removes the optimistic user message when send fails before persistence', async () => {
    vi.mocked(sourceChatApi.listSessions).mockResolvedValue([session])
    vi.mocked(sourceChatApi.getSession).mockResolvedValue({ ...session, messages: [] })
    vi.mocked(sourceChatApi.sendMessage).mockRejectedValue(new Error('network'))

    const { result } = renderHook(() => useSourceChat('source:1'), { wrapper: makeWrapper() })

    await waitFor(() => expect(result.current.currentSessionId).toBe('session:1'))

    await act(async () => {
      await result.current.sendMessage('hello')
    })

    expect(result.current.messages).toEqual([])
    expect(result.current.isStreaming).toBe(false)
  })

  it('keeps a persisted trailing human message visible when a retry send fails', async () => {
    vi.mocked(sourceChatApi.listSessions).mockResolvedValue([session])
    vi.mocked(sourceChatApi.getSession).mockResolvedValue({
      ...session,
      messages: [
        { id: 'msg-persisted', type: 'human', content: 'hello', timestamp: '2026-01-01T00:00:00Z' },
      ],
    })
    vi.mocked(sourceChatApi.sendMessage).mockRejectedValue(new Error('network'))

    const { result } = renderHook(() => useSourceChat('source:1'), { wrapper: makeWrapper() })

    await waitFor(() => expect(result.current.messages).toHaveLength(1))

    await act(async () => {
      await result.current.sendMessage('hello')
    })

    expect(result.current.messages).toHaveLength(1)
    expect(result.current.messages[0].id).toBe('msg-persisted')
    expect(result.current.isStreaming).toBe(false)
  })

  it('adopts an auto-created session when stop is pressed before create finishes', async () => {
    vi.mocked(sourceChatApi.listSessions).mockResolvedValue([])
    vi.mocked(sourceChatApi.getSession).mockResolvedValue({ ...session, id: 'session:new', messages: [] })
    let resolveCreate!: (value: SourceChatSession) => void
    vi.mocked(sourceChatApi.createSession).mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveCreate = resolve
        }),
    )
    vi.mocked(sourceChatApi.sendMessage).mockResolvedValue(sseStream([{ type: 'complete' }]) as any)

    const { result } = renderHook(() => useSourceChat('source:1'), { wrapper: makeWrapper() })

    let sendPromise!: Promise<void>
    act(() => {
      sendPromise = result.current.sendMessage('hello')
    })

    await waitFor(() => expect(result.current.isStreaming).toBe(true))

    act(() => {
      result.current.cancelStreaming()
    })

    await act(async () => {
      resolveCreate({ ...session, id: 'session:new' })
      await sendPromise
    })

    expect(result.current.currentSessionId).toBe('session:new')
    expect(result.current.isStreaming).toBe(false)
    expect(sourceChatApi.sendMessage).not.toHaveBeenCalled()

    await act(async () => {
      await result.current.sendMessage('hello again')
    })

    expect(sourceChatApi.createSession).toHaveBeenCalledTimes(1)
  })

  it('resolves authoritative session state before choosing the message id', async () => {
    const pendingTurn = {
      id: 'msg-pending',
      type: 'human' as const,
      content: 'hello',
      timestamp: '2026-01-01T00:00:00Z',
    }
    vi.mocked(sourceChatApi.listSessions).mockResolvedValue([session])
    // The session query stays in flight until the send is already under way, so
    // `messages` is still empty when the id has to be chosen.
    let resolveSession!: () => void
    vi.mocked(sourceChatApi.getSession)
      .mockImplementationOnce(
        () =>
          new Promise((resolve) => {
            resolveSession = () => resolve({ ...session, messages: [pendingTurn] })
          }),
      )
      .mockResolvedValue({ ...session, messages: [pendingTurn] })
    vi.mocked(sourceChatApi.sendMessage).mockResolvedValue(sseStream([{ type: 'complete' }]) as any)

    const { result } = renderHook(() => useSourceChat('source:1'), { wrapper: makeWrapper() })

    await waitFor(() => expect(sourceChatApi.getSession).toHaveBeenCalledTimes(1))
    expect(result.current.messages).toEqual([])

    let sendPromise!: Promise<void>
    act(() => {
      sendPromise = result.current.sendMessage('hello')
    })

    await act(async () => {
      resolveSession()
      await sendPromise
    })

    // The server still holds this turn as pending — reusing its id lets the
    // backend dedup instead of appending a duplicate human turn.
    const [, , payload] = vi.mocked(sourceChatApi.sendMessage).mock.calls[0]
    expect(payload.message_id).toBe('msg-pending')
    expect(result.current.messages).toHaveLength(1)
  })

  it('does not let a cancelled send refetch over a newer send', async () => {
    const persisted = [
      { id: 'msg-old', type: 'human' as const, content: 'first', timestamp: '2026-01-01T00:00:00Z' },
      { id: 'ai-old', type: 'ai' as const, content: 'answer', timestamp: '2026-01-01T00:00:01Z' },
    ]
    vi.mocked(sourceChatApi.listSessions).mockResolvedValue([session])
    // Second call is the cancelled send's refetch — held so it lands after the
    // next send has already added its optimistic turn.
    let resolveCancelledRefetch!: () => void
    vi.mocked(sourceChatApi.getSession)
      .mockResolvedValueOnce({ ...session, messages: persisted })
      .mockImplementationOnce(
        () =>
          new Promise((resolve) => {
            resolveCancelledRefetch = () =>
              resolve({
                ...session,
                messages: [
                  ...persisted,
                  { id: 'msg-hello', type: 'human', content: 'hello', timestamp: '2026-01-01T00:00:02Z' },
                ],
              })
          }),
      )
    vi.mocked(sourceChatApi.sendMessage).mockImplementation(abortableSend() as any)

    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    const { result } = renderHook(() => useSourceChat('source:1'), {
      wrapper: makeWrapper(client),
    })

    await waitFor(() => expect(result.current.messages).toHaveLength(2))

    let cancelled!: Promise<void>
    act(() => {
      cancelled = result.current.sendMessage('hello')
    })
    await waitFor(() => expect(result.current.messages).toHaveLength(3))

    act(() => {
      result.current.cancelStreaming()
    })
    await waitFor(() => expect(sourceChatApi.getSession).toHaveBeenCalledTimes(2))

    let newer!: Promise<void>
    act(() => {
      newer = result.current.sendMessage('second')
    })
    await waitFor(() => expect(result.current.messages).toHaveLength(4))

    act(() => {
      resolveCancelledRefetch()
    })
    // Wait for the stale snapshot to reach the cache the sync effect reads.
    await waitFor(() =>
      expect(
        client.getQueryData<SourceChatSessionWithMessages>([
          'sourceChatSession',
          'source:1',
          'session:1',
        ])?.messages,
      ).toHaveLength(3),
    )

    expect(result.current.messages.map((m) => m.content)).toEqual([
      'first',
      'answer',
      'hello',
      'second',
    ])

    // Both sends stay pending on purpose — don't leak their rejections.
    void cancelled.catch(() => {})
    void newer.catch(() => {})
  })

  it('skips session adoption when the abort came from unmount instead of stop', async () => {
    vi.mocked(sourceChatApi.listSessions).mockResolvedValue([])
    vi.mocked(sourceChatApi.getSession).mockResolvedValue({ ...session, messages: [] })
    let resolveCreate!: (value: SourceChatSession) => void
    vi.mocked(sourceChatApi.createSession).mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveCreate = resolve
        }),
    )

    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    const invalidateQueries = vi.spyOn(client, 'invalidateQueries')
    const { result, unmount } = renderHook(() => useSourceChat('source:1'), {
      wrapper: makeWrapper(client),
    })

    await waitFor(() => expect(result.current.sessions).toEqual([]))

    let sendPromise!: Promise<void>
    act(() => {
      sendPromise = result.current.sendMessage('hello')
    })
    await waitFor(() => expect(result.current.isStreaming).toBe(true))

    unmount()

    await act(async () => {
      resolveCreate({ ...session, id: 'session:new' })
      await sendPromise
    })

    expect(invalidateQueries).not.toHaveBeenCalled()
    expect(sourceChatApi.sendMessage).not.toHaveBeenCalled()
  })

  it('never logs the request config a failing send carries the auth token in', async () => {
    // Axios attaches the whole request config to its rejections, and the client
    // interceptor puts the bearer token in those headers.
    const axiosError = Object.assign(new Error('Request failed with status code 500'), {
      isAxiosError: true,
      config: { headers: { Authorization: 'Bearer secret-token' } },
      response: { status: 500, data: { detail: 'Internal error' } },
    })
    vi.mocked(sourceChatApi.listSessions).mockResolvedValue([session])
    vi.mocked(sourceChatApi.getSession).mockResolvedValue({ ...session, messages: [] })
    vi.mocked(sourceChatApi.sendMessage).mockRejectedValue(axiosError)

    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {})
    // A failing assertion must not leave the spy installed — it would silence
    // console.error for every test that runs after this one.
    try {
      const { result } = renderHook(() => useSourceChat('source:1'), { wrapper: makeWrapper() })

      await waitFor(() => expect(result.current.currentSessionId).toBe('session:1'))

      await act(async () => {
        await result.current.sendMessage('hello')
      })

      expect(consoleError).toHaveBeenCalled()
      const logged = JSON.stringify(consoleError.mock.calls)
      expect(logged).not.toContain('secret-token')
      expect(logged).not.toContain('Authorization')
    } finally {
      consoleError.mockRestore()
    }
  })

  it('keeps a send on its own session when the user switches during pre-send hydration', async () => {
    const otherSession: SourceChatSession = { ...session, id: 'session:2', title: 'Other' }
    const pendingTurn = {
      id: 'msg-pending',
      type: 'human' as const,
      content: 'hello',
      timestamp: '2026-01-01T00:00:00Z',
    }
    const otherMessages = [
      { id: 'msg-other', type: 'human' as const, content: 'other chat', timestamp: '2026-01-01T00:00:00Z' },
    ]
    vi.mocked(sourceChatApi.listSessions).mockResolvedValue([session, otherSession])
    // The first read of session:1 stays in flight until the send is already
    // past the point where it picks up authoritative state.
    let resolveFirstRead!: () => void
    let sessionOneReads = 0
    vi.mocked(sourceChatApi.getSession).mockImplementation((_sourceId, sessionId) => {
      if (sessionId === 'session:2') {
        return Promise.resolve({ ...otherSession, messages: otherMessages })
      }
      sessionOneReads += 1
      if (sessionOneReads === 1) {
        return new Promise((resolve) => {
          resolveFirstRead = () => resolve({ ...session, messages: [pendingTurn] })
        })
      }
      return Promise.resolve({ ...session, messages: [pendingTurn] })
    })
    vi.mocked(sourceChatApi.sendMessage).mockResolvedValue(
      sseStream([{ type: 'ai_message', content: 'hi' }, { type: 'complete' }]) as any
    )

    const { result } = renderHook(() => useSourceChat('source:1'), { wrapper: makeWrapper() })

    await waitFor(() => expect(result.current.currentSessionId).toBe('session:1'))

    let sendPromise!: Promise<void>
    act(() => {
      sendPromise = result.current.sendMessage('hello')
    })

    act(() => {
      result.current.switchSession('session:2')
    })
    await waitFor(() => expect(result.current.messages).toEqual(otherMessages))

    await act(async () => {
      resolveFirstRead()
      await sendPromise
    })

    // The turn belongs to the session it was composed in, and its id still comes
    // from that session's pending turn rather than the newly selected session.
    const [, sentSessionId, payload] = vi.mocked(sourceChatApi.sendMessage).mock.calls[0]
    expect(sentSessionId).toBe('session:1')
    expect(payload.message_id).toBe('msg-pending')

    // Nothing from the streamed session leaked into the selected session's view.
    expect(result.current.currentSessionId).toBe('session:2')
    expect(result.current.messages).toEqual(otherMessages)
  })

  it("adopts the switched-to session's cached messages before a submit claims the shared list", async () => {
    const otherSession: SourceChatSession = { ...session, id: 'session:2', title: 'Other' }
    const aMessages = [
      { id: 'msg-a', type: 'ai' as const, content: 'answered in A', timestamp: '2026-01-01T00:00:00Z' },
    ]
    const pendingInB = [
      { id: 'msg-b-pending', type: 'human' as const, content: 'hello', timestamp: '2026-01-01T00:00:00Z' },
    ]
    vi.mocked(sourceChatApi.listSessions).mockResolvedValue([session, otherSession])
    // The backend persists the exchange, so the send's final refetch sees it.
    let bMessages: SourceChatMessage[] = pendingInB
    vi.mocked(sourceChatApi.getSession).mockImplementation(
      (_sourceId, sessionId) =>
        Promise.resolve(
          sessionId === 'session:2'
            ? { ...otherSession, messages: bMessages }
            : { ...session, messages: aMessages },
        ) as any
    )
    vi.mocked(sourceChatApi.sendMessage).mockImplementation(() => {
      bMessages = [
        ...pendingInB,
        { id: 'ai-b', type: 'ai' as const, content: 'answer', timestamp: '2026-01-01T00:00:01Z' },
      ]
      return Promise.resolve(
        sseStream([{ type: 'ai_message', content: 'answer' }, { type: 'complete' }]) as any
      )
    })

    const { result } = renderHook(() => useSourceChat('source:1'), { wrapper: makeWrapper() })

    // Visit session:2 so its query is cached, then return to session:1 — the
    // shared list belongs to session:1 again.
    act(() => {
      result.current.switchSession('session:2')
    })
    await waitFor(() => expect(result.current.messages).toEqual(pendingInB))
    act(() => {
      result.current.switchSession('session:1')
    })
    await waitFor(() => expect(result.current.messages).toEqual(aMessages))

    // Submit in the same tick as the switch, before the session-query effect
    // can swap the list over — the send must bring session:2's transcript with
    // it instead of writing into session:1's.
    let sendPromise!: Promise<void>
    act(() => {
      result.current.switchSession('session:2')
      sendPromise = result.current.sendMessage('hello')
    })

    await act(async () => {
      await sendPromise
    })

    // The trailing turn is one session:2 already holds server-side — reusing
    // its id lets the backend dedup instead of appending a duplicate human turn.
    const [, , payload] = vi.mocked(sourceChatApi.sendMessage).mock.calls[0]
    expect(payload.message_id).toBe('msg-b-pending')
    expect(result.current.messages.map((m) => m.content)).toEqual(['hello', 'answer'])
  })

  it('rehydrates the streaming session when the user switches away and back', async () => {
    const otherSession: SourceChatSession = { ...session, id: 'session:2', title: 'Other' }
    const persisted = [
      { id: 'msg-earlier', type: 'human' as const, content: 'earlier', timestamp: '2026-01-01T00:00:00Z' },
    ]
    const otherMessages = [
      { id: 'msg-other', type: 'human' as const, content: 'other chat', timestamp: '2026-01-01T00:00:00Z' },
    ]
    vi.mocked(sourceChatApi.listSessions).mockResolvedValue([session, otherSession])
    vi.mocked(sourceChatApi.getSession).mockImplementation((_sourceId, sessionId) =>
      Promise.resolve(
        sessionId === 'session:2'
          ? { ...otherSession, messages: otherMessages }
          : { ...session, messages: persisted },
      ) as any
    )

    // A stream held open so the session can be switched mid-generation.
    const encoder = new TextEncoder()
    let push!: (event: Record<string, unknown>) => void
    let close!: () => void
    vi.mocked(sourceChatApi.sendMessage).mockResolvedValue(
      new ReadableStream<Uint8Array>({
        start(controller) {
          push = (event) => controller.enqueue(encoder.encode(`data: ${JSON.stringify(event)}\n\n`))
          close = () => controller.close()
        },
      }) as any
    )

    const { result } = renderHook(() => useSourceChat('source:1'), { wrapper: makeWrapper() })

    await waitFor(() => expect(result.current.messages).toEqual(persisted))

    let sendPromise!: Promise<void>
    act(() => {
      sendPromise = result.current.sendMessage('hello')
    })
    await waitFor(() => expect(result.current.messages).toHaveLength(2))

    await act(async () => {
      push({ type: 'ai_message', content: 'part one ' })
    })
    await waitFor(() => expect(result.current.messages).toHaveLength(3))

    act(() => {
      result.current.switchSession('session:2')
    })
    await waitFor(() => expect(result.current.messages).toEqual(otherMessages))

    // Chunks that arrive while another session is on screen must not be shown
    // there, but are still accumulated.
    await act(async () => {
      push({ type: 'ai_message', content: 'part two' })
    })
    expect(result.current.messages).toEqual(otherMessages)

    // Switching back must show session:1 again, not the other session's list.
    act(() => {
      result.current.switchSession('session:1')
    })
    await waitFor(() => expect(result.current.messages).toEqual(persisted))

    // The answer re-attaches in full, not just the chunk that arrived last.
    await act(async () => {
      push({ type: 'ai_message', content: '!' })
    })
    await waitFor(() =>
      expect(result.current.messages.at(-1)?.content).toBe('part one part two!')
    )

    await act(async () => {
      close()
      await sendPromise
    })
  })

  it('refetches persisted messages after a stream even when the cache is still fresh', async () => {
    vi.mocked(sourceChatApi.listSessions).mockResolvedValue([session])
    vi.mocked(sourceChatApi.getSession)
      .mockResolvedValueOnce({ ...session, messages: [] })
      .mockResolvedValue({
        ...session,
        messages: [
          { id: 'msg-hello', type: 'human', content: 'hello', timestamp: '2026-01-01T00:00:00Z' },
          { id: 'ai-1', type: 'ai', content: 'hi', timestamp: '2026-01-01T00:00:01Z' },
        ],
      })
    vi.mocked(sourceChatApi.sendMessage).mockResolvedValue(
      sseStream([{ type: 'ai_message', content: 'hi' }, { type: 'complete' }]) as any
    )

    // The real client sets staleTime to 5 minutes; a cached snapshot from before
    // the turn must not be served in place of the post-stream refetch.
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false, staleTime: 5 * 60 * 1000 } },
    })
    const { result } = renderHook(() => useSourceChat('source:1'), {
      wrapper: makeWrapper(client),
    })

    await waitFor(() => expect(sourceChatApi.getSession).toHaveBeenCalledTimes(1))

    await act(async () => {
      await result.current.sendMessage('hello')
    })

    expect(sourceChatApi.getSession).toHaveBeenCalledTimes(2)
    expect(result.current.messages.map((m) => m.content)).toEqual(['hello', 'hi'])
  })

  it('serializes concurrent first sends into one session create', async () => {
    vi.mocked(sourceChatApi.listSessions).mockResolvedValue([])
    vi.mocked(sourceChatApi.getSession).mockResolvedValue({ ...session, id: 'session:new', messages: [] })
    let resolveCreate!: (value: SourceChatSession) => void
    vi.mocked(sourceChatApi.createSession).mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveCreate = resolve
        }),
    )
    vi.mocked(sourceChatApi.sendMessage).mockResolvedValue(sseStream([{ type: 'complete' }]) as any)

    const { result } = renderHook(() => useSourceChat('source:1'), { wrapper: makeWrapper() })

    await waitFor(() => expect(result.current.sessions).toEqual([]))

    let firstSend!: Promise<void>
    let secondSend!: Promise<void>
    act(() => {
      firstSend = result.current.sendMessage('first')
      secondSend = result.current.sendMessage('second')
    })

    await waitFor(() => expect(result.current.isStreaming).toBe(true))
    expect(sourceChatApi.createSession).toHaveBeenCalledTimes(1)

    await act(async () => {
      resolveCreate({ ...session, id: 'session:new' })
      await Promise.all([firstSend, secondSend])
    })

    expect(sourceChatApi.createSession).toHaveBeenCalledTimes(1)
    expect(result.current.currentSessionId).toBe('session:new')
  })
})
