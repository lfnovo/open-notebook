import { describe, it, expect, vi } from 'vitest'
import type { SourceChatMessage } from '@/lib/types/api'
import { selectMessageId } from './source-chat-message'

const human = (id: string, content: string): SourceChatMessage => ({
  id,
  type: 'human',
  content,
})

const ai = (id: string): SourceChatMessage => ({ id, type: 'ai', content: 'answer' })

describe('selectMessageId', () => {
  it('reuses the trailing unanswered human id on a retry of the same content', () => {
    const generateId = vi.fn(() => 'fresh')
    const messages = [human('msg-1', 'hello')]

    expect(selectMessageId(messages, 'hello', generateId)).toBe('msg-1')
    expect(generateId).not.toHaveBeenCalled()
  })

  it('generates a fresh id when the trailing human has different content', () => {
    const generateId = vi.fn(() => 'fresh')
    const messages = [human('msg-1', 'other')]

    expect(selectMessageId(messages, 'hello', generateId)).toBe('fresh')
  })

  it('generates a fresh id after a completed exchange (trailing AI message)', () => {
    // Same content as an earlier turn, but that turn was already answered — a
    // new, distinct message must be kept, not deduplicated.
    const generateId = vi.fn(() => 'fresh')
    const messages = [human('msg-1', 'hello'), ai('ai-1')]

    expect(selectMessageId(messages, 'hello', generateId)).toBe('fresh')
  })

  it('generates a fresh id when there are no messages yet', () => {
    const generateId = vi.fn(() => 'fresh')

    expect(selectMessageId([], 'hello', generateId)).toBe('fresh')
  })
})
