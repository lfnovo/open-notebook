import type { SourceChatMessage } from '@/lib/types/api'

/** UUID v4 — works in non-secure HTTP contexts where `crypto.randomUUID` is absent. */
export function createMessageId(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID()
  }
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0
    const v = c === 'x' ? r : (r & 0x3) | 0x8
    return v.toString(16)
  })
}

/**
 * Resolve the client `message_id` for an outgoing turn.
 *
 * The backend dedupes a retry by comparing the id of the trailing (unanswered)
 * human turn against the incoming `message_id`, so a retry of the same content
 * must reuse that turn's id. Two distinct identical messages — e.g. asking the
 * same question again after an answer came back — must both be kept, so any
 * other trailing state gets a fresh id. A completed exchange always ends with an
 * AI message, so a trailing human turn is necessarily still pending.
 */
export function selectMessageId(
  messages: SourceChatMessage[],
  content: string,
  generateId: () => string = createMessageId,
): string {
  const trailing = messages[messages.length - 1]
  const isRetry = trailing?.type === 'human' && trailing.content === content
  return isRetry ? trailing.id : generateId()
}
