import type { SourceChatMessage } from '@/lib/types/api'

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
  generateId: () => string = () => crypto.randomUUID(),
): string {
  const trailing = messages[messages.length - 1]
  const isRetry = trailing?.type === 'human' && trailing.content === content
  return isRetry ? trailing.id : generateId()
}
