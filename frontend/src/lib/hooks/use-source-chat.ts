'use client'

import { useState, useCallback, useRef, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { getApiErrorMessage, getLogSafeErrorMessage } from '@/lib/utils/error-handler'
import { useTranslation } from '@/lib/hooks/use-translation'
import { sourceChatApi } from '@/lib/api/source-chat'
import { selectMessageId } from '@/lib/utils/source-chat-message'
import {
  SourceChatSession,
  SourceChatSessionWithMessages,
  SourceChatMessage,
  SourceChatContextIndicator,
  CreateSourceChatSessionRequest,
  UpdateSourceChatSessionRequest
} from '@/lib/types/api'

export function useSourceChat(sourceId: string) {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null)
  const [messages, setMessages] = useState<SourceChatMessage[]>([])
  const [isStreaming, setIsStreaming] = useState(false)
  const [contextIndicators, setContextIndicators] = useState<SourceChatContextIndicator | null>(null)
  const abortControllerRef = useRef<AbortController | null>(null)
  // Serialize auto-create on the first send so concurrent submits share one
  // in-flight create instead of racing separate sessions.
  const sessionCreatePromiseRef = useRef<Promise<string> | null>(null)
  // Monotonic per-send token: only the latest send owns the shared streaming
  // state (loading flag, final refetch).
  const sendGenerationRef = useRef(0)
  // Session a send is currently streaming into. Server snapshots for it are
  // stale by construction until that send applies its own final refetch.
  const streamingSessionRef = useRef<string | null>(null)
  // `sendMessage` closes over the state values captured when it was created —
  // reads that must see the freshest value go through these refs.
  const messagesRef = useRef<SourceChatMessage[]>([])
  const currentSessionIdRef = useRef<string | null>(null)
  // The session the local `messages` list currently represents. One list is
  // shared by every session, so a send must stop writing into it as soon as the
  // list belongs to a session other than the one being streamed.
  const messagesSessionRef = useRef<string | null>(null)
  // An explicit Stop still has to adopt an auto-created session; an abort from
  // the unmount cleanup must not touch state or the shared cache.
  const unmountedRef = useRef(false)

  const applyMessages = useCallback((
    next: SourceChatMessage[] | ((prev: SourceChatMessage[]) => SourceChatMessage[])
  ) => {
    const resolved = typeof next === 'function' ? next(messagesRef.current) : next
    messagesRef.current = resolved
    setMessages(resolved)
  }, [])

  const applySessionId = useCallback((
    next: string | null | ((prev: string | null) => string | null)
  ) => {
    const resolved = typeof next === 'function' ? next(currentSessionIdRef.current) : next
    currentSessionIdRef.current = resolved
    setCurrentSessionId(resolved)
  }, [])

  // Abort any in-flight stream when the component unmounts.
  useEffect(() => {
    unmountedRef.current = false
    return () => {
      unmountedRef.current = true
      abortControllerRef.current?.abort()
    }
  }, [])

  // Fetch sessions
  const { data: sessions = [], isLoading: loadingSessions, refetch: refetchSessions } = useQuery<SourceChatSession[]>({
    queryKey: ['sourceChatSessions', sourceId],
    queryFn: () => sourceChatApi.listSessions(sourceId),
    enabled: !!sourceId
  })

  // Fetch current session with messages
  const { data: currentSession } = useQuery({
    queryKey: ['sourceChatSession', sourceId, currentSessionId],
    queryFn: () => sourceChatApi.getSession(sourceId, currentSessionId!),
    enabled: !!sourceId && !!currentSessionId
  })

  // Shares the in-flight fetch of the session query above when both run for the
  // same session, so a send never issues a second request for the same state.
  // `staleTime: 0` is required: the client default is 5 minutes, and a cached
  // snapshot from before the turn would be applied over the streamed messages.
  const fetchSession = useCallback((sessionId: string) =>
    queryClient.fetchQuery({
      queryKey: ['sourceChatSession', sourceId, sessionId],
      queryFn: () => sourceChatApi.getSession(sourceId, sessionId),
      staleTime: 0
    })
  , [queryClient, sourceId])

  // Update messages when session changes. `isStreaming` is deliberately not a
  // dependency: re-running on the flip to false would replay stale query data
  // over the message that just finished streaming.
  useEffect(() => {
    if (!currentSession?.messages) return
    // A send streaming into this session applies the authoritative state from
    // its own final refetch — an earlier snapshot would drop newer turns. That
    // only holds while the list is still this session's: after a switch away
    // and back, the list holds another session's messages and must be replaced.
    if (
      streamingSessionRef.current === currentSession.id &&
      messagesSessionRef.current === currentSession.id
    ) return
    messagesSessionRef.current = currentSession.id
    applyMessages(currentSession.messages)
  }, [currentSession, applyMessages])

  // Auto-select most recent session when sessions are loaded
  useEffect(() => {
    if (sessions.length > 0 && !currentSessionId) {
      // Find most recent session (sessions are sorted by created date desc from API)
      const mostRecentSession = sessions[0]
      applySessionId(mostRecentSession.id)
    }
  }, [sessions, currentSessionId, applySessionId])

  // Create session mutation
  const createSessionMutation = useMutation({
    mutationFn: (data: Omit<CreateSourceChatSessionRequest, 'source_id'>) => 
      sourceChatApi.createSession(sourceId, data),
    onSuccess: (newSession) => {
      queryClient.invalidateQueries({ queryKey: ['sourceChatSessions', sourceId] })
      applySessionId(newSession.id)
      toast.success(t('chat.sessionCreated'))
    },
    onError: (err: unknown) => {
      const error = err as { response?: { data?: { detail?: string } }, message?: string };
      toast.error(getApiErrorMessage(error.response?.data?.detail || error.message, (key) => t(key), 'apiErrors.failedToCreateSession'))
    }
  })

  // Update session mutation
  const updateSessionMutation = useMutation({
    mutationFn: ({ sessionId, data }: { sessionId: string, data: UpdateSourceChatSessionRequest }) =>
      sourceChatApi.updateSession(sourceId, sessionId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sourceChatSessions', sourceId] })
      queryClient.invalidateQueries({ queryKey: ['sourceChatSession', sourceId, currentSessionId] })
      toast.success(t('chat.sessionUpdated'))
    },
    onError: (err: unknown) => {
      const error = err as { response?: { data?: { detail?: string } }, message?: string };
      toast.error(getApiErrorMessage(error.response?.data?.detail || error.message, (key) => t(key), 'apiErrors.failedToUpdateSession'))
    }
  })

  // Delete session mutation
  const deleteSessionMutation = useMutation({
    mutationFn: (sessionId: string) => 
      sourceChatApi.deleteSession(sourceId, sessionId),
    onSuccess: (_, deletedId) => {
      queryClient.invalidateQueries({ queryKey: ['sourceChatSessions', sourceId] })
      if (currentSessionId === deletedId) {
        applySessionId(null)
        messagesSessionRef.current = null
        applyMessages([])
      }
      toast.success(t('chat.sessionDeleted'))
    },
    onError: (err: unknown) => {
      const error = err as { response?: { data?: { detail?: string } }, message?: string };
      toast.error(getApiErrorMessage(error.response?.data?.detail || error.message, (key) => t(key), 'apiErrors.failedToDeleteSession'))
    }
  })

  // Send message with streaming
  const sendMessage = useCallback(async (message: string, modelOverride?: string) => {
    // Abort any previous in-flight request
    abortControllerRef.current?.abort()
    const controller = new AbortController()
    abortControllerRef.current = controller
    const signal = controller.signal
    const generation = ++sendGenerationRef.current

    const isLatestSend = () => sendGenerationRef.current === generation

    const isSuperseded = () =>
      signal.aborted ||
      !isLatestSend() ||
      (abortControllerRef.current !== null && abortControllerRef.current !== controller)

    const releaseSend = () => {
      if (!isLatestSend()) return
      streamingSessionRef.current = null
      if (abortControllerRef.current === controller) {
        abortControllerRef.current = null
      }
      setIsStreaming(false)
    }

    // Disable the composer for the whole send, including session auto-create.
    setIsStreaming(true)

    let sessionId = currentSessionIdRef.current
    let sessionJustCreated = false

    // Auto-create session if none exists
    if (!sessionId) {
      if (!sessionCreatePromiseRef.current) {
        const defaultTitle = message.length > 30 ? `${message.substring(0, 30)}...` : message
        sessionCreatePromiseRef.current = sourceChatApi
          .createSession(sourceId, { title: defaultTitle })
          .then((newSession) => newSession.id)
      }
      const createPromise = sessionCreatePromiseRef.current
      try {
        sessionId = await createPromise
      } catch (err: unknown) {
        const error = err as { response?: { data?: { detail?: string } }, message?: string };
        console.error('Failed to create chat session:', getLogSafeErrorMessage(err))
        toast.error(getApiErrorMessage(error.response?.data?.detail || error.message, (key) => t(key), 'apiErrors.failedToCreateSession'))
        releaseSend()
        return
      } finally {
        if (sessionCreatePromiseRef.current === createPromise) {
          sessionCreatePromiseRef.current = null
        }
      }
      sessionJustCreated = true

      if (isSuperseded()) {
        // Session may already exist on the backend (e.g. user pressed Stop
        // while auto-create was in flight) — adopt it so the next send does
        // not spawn another empty session. An unmount abort is not a Stop:
        // there is no next send to protect, and the cache is shared.
        if (!unmountedRef.current) {
          applySessionId((prev) => prev ?? sessionId)
          queryClient.invalidateQueries({ queryKey: ['sourceChatSessions', sourceId] })
        }
        releaseSend()
        return
      }

      applySessionId(sessionId)
      queryClient.invalidateQueries({ queryKey: ['sourceChatSessions', sourceId] })
    }

    if (isSuperseded()) {
      releaseSend()
      return
    }

    const streamSessionId = sessionId
    streamingSessionRef.current = streamSessionId

    // The turn belongs to the session it was composed in, so it is still sent
    // after the user navigates away — but the shared list then shows another
    // session and must not receive this stream's messages. The backend persists
    // the exchange, so switching back reloads it from the checkpoint. Only the
    // latest send may write: a superseded send's already-buffered events must
    // never land in the shared state the newer send is driving.
    const ownsMessages = () =>
      isLatestSend() &&
      currentSessionIdRef.current === streamSessionId &&
      messagesSessionRef.current === streamSessionId

    // The shared list must actually represent this session before the send
    // writes into it. A submit can land between `switchSession` (which changes
    // the selected session) and the session-query effect (which swaps the list
    // to that session's messages), so the list may still show the previous
    // session's transcript here — claiming it without first applying this
    // session's messages would append the turn and its streamed answer to the
    // wrong transcript, and the cached-snapshot path below would never replace
    // the list. Adopt this session's own state instead: a list that already
    // represents the session keeps its content (it can be fresher than the
    // cache — it carries optimistic turns), and a user who navigated away
    // during hydration gets neither the claim nor the overwrite.
    const adoptSessionList = (authoritative: SourceChatMessage[]): SourceChatMessage[] => {
      if (currentSessionIdRef.current !== streamSessionId) return authoritative
      if (messagesSessionRef.current === streamSessionId) return messagesRef.current
      messagesSessionRef.current = streamSessionId
      applyMessages(authoritative)
      return messagesRef.current
    }

    // `messages` only holds authoritative state once the session query has
    // resolved, and the composer is gated on `isStreaming` alone — a send can
    // land while that query is still in flight. Deriving the id from the empty
    // list would mint a fresh one for a turn the server still holds as pending,
    // and the backend would append a duplicate human turn.
    let knownMessages = messagesRef.current
    const cachedSnapshot = sessionJustCreated
      ? undefined
      : queryClient.getQueryData<SourceChatSessionWithMessages>([
          'sourceChatSession',
          sourceId,
          streamSessionId
        ])
    if (sessionJustCreated) {
      knownMessages = adoptSessionList([])
    } else if (cachedSnapshot?.messages) {
      knownMessages = adoptSessionList(cachedSnapshot.messages)
    } else if (!sessionJustCreated) {
      try {
        const hydrated = await fetchSession(streamSessionId)
        if (hydrated?.messages) {
          knownMessages = adoptSessionList(hydrated.messages)
        }
      } catch (err) {
        // The turn's id must come from authoritative state — minting one from
        // an unverified list can duplicate a pending turn the checkpoint
        // already holds (the backend dedups by id, and a blind id never
        // matches). Fail the send instead of sending with an unverified id.
        console.error('Error loading chat session before send:', getLogSafeErrorMessage(err))
        const error = err as { response?: { data?: { detail?: string } }, message?: string };
        toast.error(getApiErrorMessage(error.response?.data?.detail || error.message, (key) => t(key), 'apiErrors.failedToSendMessage'))
        releaseSend()
        return
      }
      if (isSuperseded()) {
        releaseSend()
        return
      }
    }

    // Reuse the trailing unanswered human turn's id when this is a retry of the
    // same content (so the backend dedups it) and generate a fresh identity
    // otherwise — two distinct identical messages must both be kept.
    const messageId = selectMessageId(knownMessages, message)
    const messageAlreadyPresent = knownMessages.some((m) => m.id === messageId)

    // Add the user message optimistically, carrying the same id sent to the
    // backend. The backend keys its `already_pending` check on that id, so the
    // optimistic entry must match the persisted one — a `temp-` placeholder here
    // would make a retry of this turn unable to dedup against the real uuid.
    // On a retry of a still-pending turn the id already exists — don't duplicate.
    const userMessage: SourceChatMessage = {
      id: messageId,
      type: 'human',
      content: message,
      timestamp: new Date().toISOString()
    }
    if (ownsMessages()) {
      applyMessages(prev =>
        prev.some(m => m.id === messageId) ? prev : [...prev, userMessage]
      )
    }

    try {
      const response = await sourceChatApi.sendMessage(sourceId, streamSessionId, {
        message,
        message_id: messageId,
        model_override: modelOverride
      }, signal)

      if (!response) {
        throw new Error('No response body')
      }

      const reader = response.getReader()
      const decoder = new TextDecoder()
      let aiMessage: SourceChatMessage | null = null
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')

        // Keep the last incomplete line in buffer
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const jsonStr = line.slice(6).trim()
              if (!jsonStr) continue

              const data = JSON.parse(jsonStr)
              
              if (data.type === 'ai_message') {
                // Accumulate regardless of what is on screen, so a switch away
                // and back re-attaches the full answer rather than a fragment.
                if (!aiMessage) {
                  // Created on the first content chunk to avoid an empty bubble.
                  aiMessage = {
                    id: `ai-${Date.now()}`,
                    type: 'ai',
                    content: data.content || '',
                    timestamp: new Date().toISOString()
                  }
                } else {
                  aiMessage.content += data.content || ''
                }
                if (ownsMessages()) {
                  const streamed = { ...aiMessage }
                  applyMessages(prev =>
                    prev.some(msg => msg.id === streamed.id)
                      ? prev.map(msg => msg.id === streamed.id ? streamed : msg)
                      : [...prev, streamed]
                  )
                }
              } else if (data.type === 'context_indicators') {
                // A superseded send's buffered event must not overwrite the
                // indicators the current send is producing.
                if (isLatestSend()) {
                  setContextIndicators(data.data)
                }
              } else if (data.type === 'error') {
                throw new Error(data.message || 'Stream error')
              }
            } catch (e) {
              if (e instanceof SyntaxError) {
                console.error('Error parsing SSE data:', e)
              } else {
                throw e
              }
            }
          }
        }
      }
    } catch (err: unknown) {
      // Cancelled by the user — the finally block still refetches persisted messages.
      if (err instanceof DOMException && err.name === 'AbortError') {
        return
      }
      // Drop only a bubble we added in this send — a retry reuses a persisted id
      // that must stay visible until the refetch completes.
      if (!isSuperseded() && !messageAlreadyPresent && ownsMessages()) {
        applyMessages(prev => prev.filter(m => m.id !== messageId))
      }
      const error = err as { response?: { data?: { detail?: string } }, message?: string };
      console.error('Error sending message:', getLogSafeErrorMessage(err))
      toast.error(getApiErrorMessage(error.response?.data?.detail || error.message, (key) => t(key), 'apiErrors.failedToSendMessage'))
    } finally {
      // A send replaced by a newer one must not clear the newer stream's loading
      // state nor apply server state over its messages. A user-initiated cancel
      // keeps its generation, so it still falls through and restores the
      // persisted user message.
      if (isLatestSend()) {
        setIsStreaming(false)
        if (abortControllerRef.current === controller) {
          abortControllerRef.current = null
        }
        if (!unmountedRef.current) {
          try {
            const persisted = await fetchSession(streamSessionId)
            // A newer send or a session switch owns the messages now.
            if (isLatestSend() && ownsMessages() && persisted?.messages) {
              applyMessages(persisted.messages)
            }
          } catch (err) {
            console.error('Error refreshing chat session:', getLogSafeErrorMessage(err))
          }
        }
        if (isLatestSend()) {
          streamingSessionRef.current = null
        }
      }
    }
  }, [sourceId, applyMessages, applySessionId, fetchSession, queryClient, t])

  // Cancel streaming
  const cancelStreaming = useCallback(() => {
    abortControllerRef.current?.abort()
    abortControllerRef.current = null
    setIsStreaming(false)
  }, [])

  // Switch session
  const switchSession = useCallback((sessionId: string) => {
    applySessionId(sessionId)
    setContextIndicators(null)
  }, [applySessionId])

  // Create session
  const createSession = useCallback((data: Omit<CreateSourceChatSessionRequest, 'source_id'>) => {
    return createSessionMutation.mutate(data)
  }, [createSessionMutation])

  // Update session
  const updateSession = useCallback((sessionId: string, data: UpdateSourceChatSessionRequest) => {
    return updateSessionMutation.mutate({ sessionId, data })
  }, [updateSessionMutation])

  // Delete session
  const deleteSession = useCallback((sessionId: string) => {
    return deleteSessionMutation.mutate(sessionId)
  }, [deleteSessionMutation])

  return {
    // State
    sessions,
    currentSession: sessions.find(s => s.id === currentSessionId),
    currentSessionId,
    messages,
    isStreaming,
    contextIndicators,
    loadingSessions,
    
    // Actions
    createSession,
    updateSession,
    deleteSession,
    switchSession,
    sendMessage,
    cancelStreaming,
    refetchSessions
  }
}
