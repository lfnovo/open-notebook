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
    vi.mocked(chatApi.sendMessage).mockRejectedValue(new Error('Network Error'))

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

  // Creating the session enables the session query, which comes back with no
  // messages while the reply is still being generated. That used to replace
  // the list and hide the question until the answer arrived (#1391).
  it('keeps the first message of a new chat visible while the reply is pending', async () => {
    vi.mocked(chatApi.listSessions).mockResolvedValue([])
    vi.mocked(chatApi.createSession).mockResolvedValue(session)
    vi.mocked(chatApi.getSession).mockResolvedValue({ ...session, messages: [] })
    let reply!: (value: Awaited<ReturnType<typeof chatApi.sendMessage>>) => void
    vi.mocked(chatApi.sendMessage).mockReturnValue(new Promise(resolve => { reply = resolve }))

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

    const messages = [
      { id: 'm1', type: 'human' as const, content: 'hello' },
      { id: 'm2', type: 'ai' as const, content: 'hi there' },
    ]
    vi.mocked(chatApi.getSession).mockResolvedValue({ ...session, messages })
    let sent: boolean | undefined
    await act(async () => {
      reply({ session_id: session.id, messages })
      sent = await sending
    })

    expect(sent).toBe(true)
    expect(result.current.messages.map(m => m.content)).toEqual(['hello', 'hi there'])
  })
})
