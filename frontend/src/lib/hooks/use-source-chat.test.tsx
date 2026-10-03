import { ReactNode } from 'react'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { useSourceChat } from './use-source-chat'
import { sourceChatApi } from '@/lib/api/source-chat'

vi.mock('@/lib/api/source-chat', () => ({
  sourceChatApi: {
    listSessions: vi.fn(),
    getSession: vi.fn(),
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
})
