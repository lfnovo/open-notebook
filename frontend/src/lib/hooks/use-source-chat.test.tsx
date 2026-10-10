import { ReactNode } from 'react'
import { act, renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { useSourceChat } from './use-source-chat'
import { sourceChatApi } from '@/lib/api/source-chat'

vi.mock('@/lib/api/source-chat', () => ({
  sourceChatApi: {
    listSessions: vi.fn(),
    getSession: vi.fn(),
    createSession: vi.fn(),
    sendMessage: vi.fn(),
  },
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

const session = {
  id: 'chat_session:abc',
  title: 'Session',
  source_id: 'source:xyz',
  created: '2026-01-01T00:00:00',
  updated: '2026-01-01T00:00:00',
}

describe('useSourceChat', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  // The context badge used to come only from the SSE event, so it disappeared
  // after a refresh even though GET session returns it (#1393).
  it('restores context indicators from the loaded session', async () => {
    const indicators = { sources: ['source:xyz'], insights: [], notes: [] }
    vi.mocked(sourceChatApi.listSessions).mockResolvedValue([
      {
        id: 'chat_session:abc',
        title: 'Session',
        source_id: 'source:xyz',
        created: '2026-01-01T00:00:00',
        updated: '2026-01-01T00:00:00',
      },
    ])
    vi.mocked(sourceChatApi.getSession).mockResolvedValue({
      id: 'chat_session:abc',
      title: 'Session',
      source_id: 'source:xyz',
      created: '2026-01-01T00:00:00',
      updated: '2026-01-01T00:00:00',
      messages: [{ id: 'm1', type: 'human', content: 'hello' }],
      context_indicators: indicators,
    })

    const { result } = renderHook(() => useSourceChat('source:xyz'), { wrapper })

    await waitFor(() => expect(result.current.contextIndicators).toEqual(indicators))
    expect(result.current.messages).toHaveLength(1)
  })

  // A failed send used to resolve like a successful one, so the composer had
  // no way to give the typed text back (#1391).
  it('resolves to false when sending fails', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => {})
    vi.mocked(sourceChatApi.listSessions).mockResolvedValue([session])
    vi.mocked(sourceChatApi.getSession).mockResolvedValue({ ...session, messages: [] })
    vi.mocked(sourceChatApi.sendMessage).mockRejectedValue(new TypeError('Failed to fetch'))

    const { result } = renderHook(() => useSourceChat('source:xyz'), { wrapper })
    await waitFor(() => expect(result.current.currentSessionId).toBe(session.id))

    let sent: boolean | undefined
    await act(async () => {
      sent = await result.current.sendMessage('hello')
    })

    expect(sent).toBe(false)
    expect(result.current.messages).toEqual([])
  })

  // Creating the session enables the session query, which comes back with no
  // messages while the answer is still streaming. That used to replace the
  // list and hide the question (#1391).
  it('keeps the first message of a new chat visible while the answer streams', async () => {
    const indicators = { sources: ['source:xyz'], insights: [], notes: [] }
    vi.mocked(sourceChatApi.listSessions).mockResolvedValue([])
    vi.mocked(sourceChatApi.createSession).mockResolvedValue(session)
    vi.mocked(sourceChatApi.getSession).mockResolvedValue({
      ...session,
      messages: [],
      context_indicators: indicators,
    })
    let stream!: ReadableStreamDefaultController
    vi.mocked(sourceChatApi.sendMessage).mockResolvedValue(
      new ReadableStream({ start(controller) { stream = controller } })
    )

    const { result } = renderHook(() => useSourceChat('source:xyz'), { wrapper })
    await waitFor(() => expect(sourceChatApi.listSessions).toHaveBeenCalled())

    let sending!: Promise<boolean>
    act(() => {
      sending = result.current.sendMessage('hello')
    })

    // The badge shows once the empty session has loaded and its effect has run
    await waitFor(() => expect(result.current.contextIndicators).toEqual(indicators))

    expect(result.current.messages.map(m => m.content)).toEqual(['hello'])

    const messages = [
      { id: 'm1', type: 'human' as const, content: 'hello' },
      { id: 'm2', type: 'ai' as const, content: 'hi there' },
    ]
    vi.mocked(sourceChatApi.getSession).mockResolvedValue({ ...session, messages })
    let sent: boolean | undefined
    await act(async () => {
      stream.enqueue(new TextEncoder().encode('data: {"type":"ai_message","content":"hi there"}\n\n'))
      stream.close()
      sent = await sending
    })

    expect(sent).toBe(true)
    await waitFor(() =>
      expect(result.current.messages.map(m => m.content)).toEqual(['hello', 'hi there'])
    )
  })
})
