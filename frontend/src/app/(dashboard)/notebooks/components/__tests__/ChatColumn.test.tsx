/* eslint-disable @typescript-eslint/no-explicit-any */
import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { ChatColumn } from '../ChatColumn'
import { useSources } from '@/lib/hooks/use-sources'
import { useNotes } from '@/lib/hooks/use-notes'
import { useNotebookChat } from '@/lib/hooks/useNotebookChat'

// Mock the hooks
vi.mock('@/lib/hooks/use-sources')
vi.mock('@/lib/hooks/use-notes')
vi.mock('@/lib/hooks/useNotebookChat')
vi.mock('@/components/source/ChatPanel', () => ({
  ChatPanel: () => <div data-testid="chat-panel" />
}))

describe('ChatColumn', () => {
  const mockProps = {
    notebookId: 'test-notebook',
    contextSelections: {
      sources: {},
      notes: {}
    }
  }

  it('shows loading spinner when fetching data', () => {
    vi.mocked(useSources).mockReturnValue({ data: [], isLoading: true } as any)
    vi.mocked(useNotes).mockReturnValue({ data: [], isLoading: true } as any)
    vi.mocked(useNotebookChat).mockReturnValue({ messages: [], isSending: false } as any)

    render(<ChatColumn {...mockProps} />)
    
    // Should show loading spinner
    expect(screen.getByTestId('loading-spinner')).toBeDefined()
  })

  it('renders chat panel when data is loaded', () => {
    vi.mocked(useSources).mockReturnValue({ data: [], isLoading: false } as any)
    vi.mocked(useNotes).mockReturnValue({ data: [], isLoading: false } as any)
    vi.mocked(useNotebookChat).mockReturnValue({ 
      messages: [], 
      isSending: false,
      tokenCount: 0,
      charCount: 0,
      sessions: [],
      currentSessionId: null
    } as any)

    render(<ChatColumn {...mockProps} />)
    
    // Should show chat panel
    expect(screen.getByTestId('chat-panel')).toBeDefined()
  })
})
