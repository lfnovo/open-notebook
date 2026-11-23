import { ReactNode } from 'react'
import { act, renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { toast } from 'sonner'
import { useNotebookChat } from './use-notebook-chat'
import { chatApi } from '@/lib/api/chat'

vi.mock('@/lib/api/chat', () => ({
  chatApi: {
    listSessions: vi.fn(),
    getSession: vi.fn(),
    createSession: vi.fn(),
    buildContext: vi.fn(),
    sendMessageStream: vi.fn(),
  },
  ChatStreamError: class ChatStreamError extends Error {},
}))

vi.mock('@/lib/hooks/use-translation', () => ({
  useTranslation: () => ({ t: (key: string) => key }),
}))

vi.mock('sonner', () => ({
  toast: { error: vi.fn(), success: vi.fn() },
}))

function wrapper({ children }: { children: ReactNode }) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
}

/** SSE body that already holds `events` and is closed. */
function sseStream(events: Array<Record<string, unknown>>) {
  const text = events.map(event => `data: ${JSON.stringify(event)}\n\n`).join('')
  return new ReadableStream<Uint8Array>({
    start(controller) {
      controller.enqueue(new TextEncoder().encode(text))
      controller.close()
    },
  })
}

/** SSE body the test pushes events into. */
function openStream() {
  let controller!: ReadableStreamDefaultController<Uint8Array>
  const stream = new ReadableStream<Uint8Array>({
    start(c) {
      controller = c
    },
  })
  return {
    stream,
    send: (event: Record<string, unknown>) =>
      controller.enqueue(new TextEncoder().encode(`data: ${JSON.stringify(event)}\n\n`)),
    close: () => controller.close(),
    fail: (error: Error) => controller.error(error),
  }
}

// Defined once so the hook's buildContext callback keeps a stable identity
const params = {
  notebookId: 'notebook:1',
  sources: [],
  notes: [],
  contextSelections: { sources: {}, notes: {} },
}

const session = {
  id: 'chat_session:1',
  title: 'hello',
  notebook_id: 'notebook:1',
  created: '2026-01-01T00:00:00',
  updated: '2026-01-01T00:00:00',
}

describe('useNotebookChat', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.spyOn(console, 'error').mockImplementation(() => {})
    vi.mocked(chatApi.buildContext).mockResolvedValue({
      context: { sources: [], notes: [] },
      token_count: 0,
      char_count: 0,
    })
  })

  // A failed send used to resolve like a successful one, so the composer had
  // no way to give the typed text back (#1391).
  it('resolves to false when sending fails', async () => {
    vi.mocked(chatApi.listSessions).mockResolvedValue([session])
    vi.mocked(chatApi.getSession).mockResolvedValue({ ...session, messages: [] })
    vi.mocked(chatApi.sendMessageStream).mockRejectedValue(new Error('Network Error'))

    const { result } = renderHook(() => useNotebookChat(params), { wrapper })
    await waitFor(() => expect(result.current.currentSessionId).toBe(session.id))

    let sent: boolean | undefined
    await act(async () => {
      sent = await result.current.sendMessage('hello')
    })

    expect(sent).toBe(false)
    expect(toast.error).toHaveBeenCalled()
    expect(result.current.messages).toEqual([])
  })

  // The chat must count as sending while its session is still being created,
  // so the composer and session switcher stay disabled for the whole send (#1597).
  it('marks the chat as sending while a new session is being created', async () => {
    vi.mocked(chatApi.listSessions).mockResolvedValue([])
    let createResolve!: (value: Awaited<ReturnType<typeof chatApi.createSession>>) => void
    vi.mocked(chatApi.createSession).mockReturnValue(new Promise(resolve => { createResolve = resolve }))
    vi.mocked(chatApi.getSession).mockResolvedValue({ ...session, messages: [] })
    vi.mocked(chatApi.sendMessageStream).mockResolvedValue(sseStream([]))

    const { result } = renderHook(() => useNotebookChat(params), { wrapper })
    await waitFor(() => expect(chatApi.listSessions).toHaveBeenCalled())

    let sending!: Promise<boolean>
    act(() => {
      sending = result.current.sendMessage('hello')
    })

    await waitFor(() => expect(chatApi.createSession).toHaveBeenCalled())
    expect(result.current.isSending).toBe(true)

    await act(async () => {
      createResolve(session)
      await sending
    })

    expect(result.current.isSending).toBe(false)
  })

  it('shows loaded session history after a send fails', async () => {
    vi.mocked(chatApi.listSessions).mockResolvedValue([])
    let createResolve!: (value: Awaited<ReturnType<typeof chatApi.createSession>>) => void
    vi.mocked(chatApi.createSession).mockReturnValue(new Promise(resolve => { createResolve = resolve }))
    let historyResolve!: (value: Awaited<ReturnType<typeof chatApi.getSession>>) => void
    vi.mocked(chatApi.getSession).mockReturnValue(new Promise(resolve => { historyResolve = resolve }))
    let sendReject!: (reason: Error) => void
    vi.mocked(chatApi.sendMessageStream).mockReturnValue(new Promise((_, reject) => { sendReject = reject }))

    const { result } = renderHook(() => useNotebookChat(params), { wrapper })
    await waitFor(() => expect(chatApi.listSessions).toHaveBeenCalled())

    let sending!: Promise<boolean>
    act(() => {
      sending = result.current.sendMessage('new question')
    })

    await waitFor(() => expect(chatApi.createSession).toHaveBeenCalled())
    await act(async () => {
      createResolve(session)
    })
    await waitFor(() => expect(chatApi.getSession).toHaveBeenCalled())

    const history = [{ id: 'old-message', type: 'human' as const, content: 'previous question' }]
    await act(async () => {
      historyResolve({ ...session, messages: history })
      await waitFor(() => expect(result.current.currentSession).toHaveProperty('messages', history))
    })
    expect(result.current.messages.map(message => message.content)).toEqual(['new question'])

    await act(async () => {
      sendReject(new Error('Network Error'))
      expect(await sending).toBe(false)
    })

    expect(result.current.messages).toEqual(history)
  })

  it('keeps streamed content when the final refetch fails', async () => {
    vi.mocked(chatApi.listSessions).mockResolvedValue([session])
    vi.mocked(chatApi.getSession)
      .mockResolvedValueOnce({ ...session, messages: [] })
      .mockRejectedValueOnce(new Error('Refetch failed'))
    vi.mocked(chatApi.sendMessageStream).mockResolvedValue(
      sseStream([{ type: 'token', content: 'hi there' }, { type: 'complete', content: 'hi there' }])
    )

    const { result } = renderHook(() => useNotebookChat(params), { wrapper })
    await waitFor(() => expect(result.current.currentSessionId).toBe(session.id))
    await waitFor(() => expect(chatApi.getSession).toHaveBeenCalledTimes(1))

    await act(async () => {
      expect(await result.current.sendMessage('hello')).toBe(true)
    })

    expect(result.current.messages.map(message => message.content)).toEqual(['hello', 'hi there'])
  })

  // Creating the session enables the session query, which comes back with no
  // messages while the reply is still being generated. That used to replace
  // the list and hide the question until the answer arrived (#1391).
  it('keeps the first message of a new chat visible while the reply is pending', async () => {
    vi.mocked(chatApi.listSessions).mockResolvedValue([])
    vi.mocked(chatApi.createSession).mockResolvedValue(session)
    let serverMessages: Array<{ id: string, type: 'human' | 'ai', content: string }> = []
    vi.mocked(chatApi.getSession).mockImplementation(
      async () => ({ ...session, messages: serverMessages })
    )
    const stream = openStream()
    vi.mocked(chatApi.sendMessageStream).mockResolvedValue(stream.stream)

    const { result } = renderHook(() => useNotebookChat(params), { wrapper })
    await waitFor(() => expect(chatApi.listSessions).toHaveBeenCalled())

    let sending!: Promise<boolean>
    act(() => {
      sending = result.current.sendMessage('hello')
    })

    // Wait until the empty session has loaded, then let its effects run
    await waitFor(() => expect(result.current.currentSession).toHaveProperty('messages'))
    await act(async () => {})

    expect(result.current.messages.map(m => m.content)).toEqual(['hello'])

    serverMessages = [
      { id: 'm1', type: 'human', content: 'hello' },
      { id: 'm2', type: 'ai', content: 'hi there' },
    ]
    let sent: boolean | undefined
    await act(async () => {
      stream.send({ type: 'token', content: 'hi ' })
      stream.send({ type: 'complete', content: 'hi there' })
      stream.close()
      sent = await sending
    })

    expect(sent).toBe(true)
    expect(result.current.messages.map(m => m.content)).toEqual(['hello', 'hi there'])
  })

  // A stopped turn keeps its partial answer: the composer must treat it as a
  // successful send (draft stays cleared) and the bubble must survive.
  it('keeps the partial answer when the turn is stopped', async () => {
    vi.mocked(chatApi.listSessions).mockResolvedValue([session])
    vi.mocked(chatApi.getSession).mockResolvedValue({ ...session, messages: [] })
    const stream = openStream()
    vi.mocked(chatApi.sendMessageStream).mockImplementation(
      (_data, signal) => new Promise((resolve, reject) => {
        signal?.addEventListener('abort', () => {
          stream.fail(new DOMException('Aborted', 'AbortError'))
          reject(new DOMException('Aborted', 'AbortError'))
        })
        resolve(stream.stream)
      })
    )

    const { result } = renderHook(() => useNotebookChat(params), { wrapper })
    await waitFor(() => expect(result.current.currentSessionId).toBe(session.id))

    let sending!: Promise<boolean>
    await act(async () => {
      sending = result.current.sendMessage('hello')
      stream.send({ type: 'token', content: 'part' })
    })
    await waitFor(() => expect(result.current.messages.map(m => m.content)).toEqual(['hello', 'part']))

    vi.mocked(chatApi.getSession).mockResolvedValue({
      ...session,
      messages: [
        { id: 'm1', type: 'human' as const, content: 'hello' },
        { id: 'm2', type: 'ai' as const, content: 'part' },
      ],
    })

    await act(async () => {
      result.current.stopStreaming()
      expect(await sending).toBe(true)
    })

    expect(result.current.messages.map(m => m.content)).toEqual(['hello', 'part'])
  })
})