'use client'

import { useState, useCallback, useRef, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { getApiErrorMessage } from '@/lib/utils/error-handler'
import { useTranslation } from '@/lib/hooks/use-translation'
import { sourceChatApi } from '@/lib/api/source-chat'
import { selectMessageId } from '@/lib/utils/source-chat-message'
import {
  SourceChatSession,
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

  // Abort any in-flight stream when the component unmounts.
  useEffect(() => {
    return () => {
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
  const { data: currentSession, refetch: refetchCurrentSession } = useQuery({
    queryKey: ['sourceChatSession', sourceId, currentSessionId],
    queryFn: () => sourceChatApi.getSession(sourceId, currentSessionId!),
    enabled: !!sourceId && !!currentSessionId
  })

  // Update messages when session changes
  useEffect(() => {
    if (currentSession?.messages) {
      setMessages(currentSession.messages)
    }
    // Also clears the badge when the session goes away (deleted / switched).
    setContextIndicators(currentSession?.context_indicators ?? null)
  }, [currentSession])

  // Auto-select most recent session when sessions are loaded
  useEffect(() => {
    if (sessions.length > 0 && !currentSessionId) {
      // Find most recent session (sessions are sorted by created date desc from API)
      const mostRecentSession = sessions[0]
      setCurrentSessionId(mostRecentSession.id)
    }
  }, [sessions, currentSessionId])

  // Create session mutation
  const createSessionMutation = useMutation({
    mutationFn: (data: Omit<CreateSourceChatSessionRequest, 'source_id'>) => 
      sourceChatApi.createSession(sourceId, data),
    onSuccess: (newSession) => {
      queryClient.invalidateQueries({ queryKey: ['sourceChatSessions', sourceId] })
      setCurrentSessionId(newSession.id)
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
        setCurrentSessionId(null)
        setMessages([])
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

    const isSuperseded = () =>
      signal.aborted ||
      (abortControllerRef.current !== null && abortControllerRef.current !== controller)

    const clearOwnStreamingState = () => {
      if (abortControllerRef.current === controller) {
        abortControllerRef.current = null
        setIsStreaming(false)
      }
    }

    // Disable the composer for the whole send, including session auto-create.
    setIsStreaming(true)

    let sessionId = currentSessionId

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
        console.error('Failed to create chat session:', error)
        toast.error(getApiErrorMessage(error.response?.data?.detail || error.message, (key) => t(key), 'apiErrors.failedToCreateSession'))
        clearOwnStreamingState()
        return
      } finally {
        if (sessionCreatePromiseRef.current === createPromise) {
          sessionCreatePromiseRef.current = null
        }
      }

      if (isSuperseded()) {
        // Session may already exist on the backend (e.g. user pressed Stop
        // while auto-create was in flight) — adopt it so the next send does
        // not spawn another empty session.
        setCurrentSessionId((prev) => prev ?? sessionId)
        queryClient.invalidateQueries({ queryKey: ['sourceChatSessions', sourceId] })
        clearOwnStreamingState()
        return
      }

      setCurrentSessionId(sessionId)
      queryClient.invalidateQueries({ queryKey: ['sourceChatSessions', sourceId] })
    }

    if (isSuperseded()) {
      clearOwnStreamingState()
      return
    }

    // Reuse the trailing unanswered human turn's id when this is a retry of the
    // same content (so the backend dedups it) and generate a fresh identity
    // otherwise — two distinct identical messages must both be kept.
    const messageId = selectMessageId(messages, message)
    const messageAlreadyPresent = messages.some((m) => m.id === messageId)

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
    setMessages(prev =>
      prev.some(m => m.id === messageId) ? prev : [...prev, userMessage]
    )

    try {
      const response = await sourceChatApi.sendMessage(sourceId, sessionId, {
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
                // Create AI message on first content chunk to avoid empty bubble
                if (!aiMessage) {
                  aiMessage = {
                    id: `ai-${Date.now()}`,
                    type: 'ai',
                    content: data.content || '',
                    timestamp: new Date().toISOString()
                  }
                  setMessages(prev => [...prev, aiMessage!])
                } else {
                  aiMessage.content += data.content || ''
                  setMessages(prev =>
                    prev.map(msg => msg.id === aiMessage!.id
                      ? { ...msg, content: aiMessage!.content }
                      : msg
                    )
                  )
                }
              } else if (data.type === 'context_indicators') {
                setContextIndicators(data.data)
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
      if (!isSuperseded() && !messageAlreadyPresent) {
        setMessages(prev => prev.filter(m => m.id !== messageId))
      }
      const error = err as { response?: { data?: { detail?: string } }, message?: string };
      console.error('Error sending message:', error)
      toast.error(getApiErrorMessage(error.response?.data?.detail || error.message, (key) => t(key), 'apiErrors.failedToSendMessage'))
    } finally {
      // A superseded send (replaced by a newer one) must not clear the newer
      // stream's loading state or refetch over its messages. A user-initiated
      // cancel sets the ref to null (and clears isStreaming itself), so it still
      // falls through to refetch the persisted user message.
      const superseded =
        abortControllerRef.current !== null && abortControllerRef.current !== controller
      if (!superseded) {
        setIsStreaming(false)
        // Refetch session to get persisted messages
        refetchCurrentSession()
      }
    }
  }, [sourceId, currentSessionId, messages, refetchCurrentSession, queryClient, t])

  // Cancel streaming
  const cancelStreaming = useCallback(() => {
    abortControllerRef.current?.abort()
    abortControllerRef.current = null
    setIsStreaming(false)
  }, [])

  // Switch session
  const switchSession = useCallback((sessionId: string) => {
    setCurrentSessionId(sessionId)
    setContextIndicators(null)
  }, [])

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
