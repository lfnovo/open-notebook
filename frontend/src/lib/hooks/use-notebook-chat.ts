'use client'

import { useState, useCallback, useEffect, useRef } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { getApiErrorMessage } from '@/lib/utils/error-handler'
import { useTranslation } from '@/lib/hooks/use-translation'
import { chatApi, ChatStreamError } from '@/lib/api/chat'
import { QUERY_KEYS } from '@/lib/api/query-client'
import {
  NotebookChatMessage,
  CreateNotebookChatSessionRequest,
  UpdateNotebookChatSessionRequest,
  SourceListResponse,
  NoteResponse
} from '@/lib/types/api'
import { ContextSelections } from '@/app/(dashboard)/notebooks/[id]/page'

interface UseNotebookChatParams {
  notebookId: string
  sources: SourceListResponse[]
  notes: NoteResponse[]
  contextSelections: ContextSelections
}

// How long to keep polling for the server to finish persisting a stopped turn.
const SETTLE_TIMEOUT_MS = 5000
const SETTLE_POLL_MS = 150

// Error codes the stream endpoint authors itself, mapped to their keys. The
// literals matter: the locale parity test scans for used keys.
const STREAM_ERROR_KEYS: Record<string, string> = {
  timeout: 'chat.errors.timeout',
  timeout_partial_kept: 'chat.errors.timeout_partial_kept',
  timeout_partial_lost: 'chat.errors.timeout_partial_lost',
  empty_reply: 'chat.errors.empty_reply',
}

const sleep = (ms: number) => new Promise(resolve => setTimeout(resolve, ms))

export function useNotebookChat({ notebookId, sources, notes, contextSelections }: UseNotebookChatParams) {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null)
  const [messages, setMessages] = useState<NotebookChatMessage[]>([])
  const [isSending, setIsSending] = useState(false)
  // Same as isSending, but readable from the session effect without re-running it
  const sendingRef = useRef(false)
  // True for the whole lifetime of a streamed turn (until it has resynced), so
  // a refetch landing mid-stream cannot replace the messages and drop the
  // in-flight answer bubble.
  const streamingRef = useRef(false)
  // A failed refetch after a successful send can leave currentSession stale.
  // Keep the response messages for the effect pass that follows that send.
  const preserveMessagesAfterSendRef = useRef(false)
  // The in-flight turn's controller. Cleanup is scoped to it, so a send made
  // right after a Stop is not clobbered by the aborted turn's late cleanup.
  const abortControllerRef = useRef<AbortController | null>(null)
  const [tokenCount, setTokenCount] = useState<number>(0)
  const [charCount, setCharCount] = useState<number>(0)
  // Pending model override for when user changes model before a session exists
  const [pendingModelOverride, setPendingModelOverride] = useState<string | null>(null)

  // Fetch sessions for this notebook
  const {
    data: sessions = [],
    isLoading: loadingSessions,
    refetch: refetchSessions
  } = useQuery({
    queryKey: QUERY_KEYS.notebookChatSessions(notebookId),
    queryFn: () => chatApi.listSessions(notebookId),
    enabled: !!notebookId
  })

  // Fetch current session with messages
  const {
    data: currentSession,
    refetch: refetchCurrentSession
  } = useQuery({
    queryKey: QUERY_KEYS.notebookChatSession(currentSessionId!),
    queryFn: () => chatApi.getSession(currentSessionId!),
    enabled: !!notebookId && !!currentSessionId
  })

  // Update messages when current session changes. Skipped while a send is in
  // flight or a stream is still rendering: the session can load mid-send
  // without the optimistic message, and would hide it until the reply arrives
  // (#1391, #1618).
  useEffect(() => {
    if (preserveMessagesAfterSendRef.current && !sendingRef.current) {
      preserveMessagesAfterSendRef.current = false
      return
    }
    if (currentSession?.messages && !sendingRef.current && !streamingRef.current) {
      setMessages(currentSession.messages)
    }
  }, [currentSession, isSending])

  // Auto-select most recent session when sessions are loaded
  useEffect(() => {
    if (sessions.length > 0 && !currentSessionId) {
      // Sessions are sorted by created date desc from API
      const mostRecentSession = sessions[0]
      setCurrentSessionId(mostRecentSession.id)
    }
  }, [sessions, currentSessionId])

  // Create session mutation
  const createSessionMutation = useMutation({
    mutationFn: (data: CreateNotebookChatSessionRequest) =>
      chatApi.createSession(data),
    onSuccess: (newSession) => {
      queryClient.invalidateQueries({
        queryKey: QUERY_KEYS.notebookChatSessions(notebookId)
      })
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
    mutationFn: ({ sessionId, data }: {
      sessionId: string
      data: UpdateNotebookChatSessionRequest
    }) => chatApi.updateSession(sessionId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: QUERY_KEYS.notebookChatSessions(notebookId)
      })
      queryClient.invalidateQueries({
        queryKey: QUERY_KEYS.notebookChatSession(currentSessionId!)
      })
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
      chatApi.deleteSession(sessionId),
    onSuccess: (_, deletedId) => {
      queryClient.invalidateQueries({
        queryKey: QUERY_KEYS.notebookChatSessions(notebookId)
      })
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

  // Build context from sources and notes based on user selections
  const buildContext = useCallback(async () => {
    // Build context_config mapping IDs to selection modes
    const context_config: { sources: Record<string, string>, notes: Record<string, string> } = {
      sources: {},
      notes: {}
    }

    // Map source selections
    sources.forEach(source => {
      const mode = contextSelections.sources[source.id]
      if (mode === 'insights') {
        context_config.sources[source.id] = 'insights'
      } else if (mode === 'full') {
        context_config.sources[source.id] = 'full content'
      } else {
        context_config.sources[source.id] = 'not in'
      }
    })

    // Map note selections
    notes.forEach(note => {
      const mode = contextSelections.notes[note.id]
      if (mode === 'full') {
        context_config.notes[note.id] = 'full content'
      } else {
        context_config.notes[note.id] = 'not in'
      }
    })

    // Call API to build context with actual content
    const response = await chatApi.buildContext({
      notebook_id: notebookId,
      context_config
    })

    // Store token and char counts
    setTokenCount(response.token_count)
    setCharCount(response.char_count)

    return response.context
  }, [notebookId, sources, notes, contextSelections])

  // Wait until a stopped turn has been persisted server-side. The endpoint
  // keeps the partial answer (or the question alone); refetching before its
  // cancellation handler has settled would show a thread without it. The
  // count is the signal: it reaches `minMessages` only once the turn is
  // written, and no two equal reads mean the same thing.
  const waitForSettlement = useCallback(async (sessionId: string, minMessages: number) => {
    const deadline = Date.now() + SETTLE_TIMEOUT_MS
    let latest: Awaited<ReturnType<typeof chatApi.getSession>> | null = null

    while (Date.now() < deadline) {
      await sleep(SETTLE_POLL_MS)
      try {
        const session = await chatApi.getSession(sessionId)
        latest = session
        if (session.messages.length >= minMessages) return latest
      } catch {
        return latest
      }
    }
    return latest
  }, [])

  // After an abort that beat the acknowledgement, look for the question in the
  // thread. If the server stored it, the turn is accepted after all and a retry
  // would duplicate it.
  const reconciledAbort = useCallback(async (sessionId: string, baseline: number, message: string) => {
    try {
      const session = await chatApi.getSession(sessionId)
      const lastHuman = [...session.messages].reverse().find(m => m.type === 'human')
      if (session.messages.length > baseline && lastHuman?.content === message) {
        return session
      }
    } catch {
      // Treat an unreadable session as "not stored".
    }
    return null
  }, [])

  // Send message (SSE streaming; tokens render as they arrive)
  const sendMessage = useCallback(async (message: string, modelOverride?: string): Promise<boolean> => {
    // Mark sending before any await (including session creation) so the
    // composer and session switcher stay disabled for the whole send (#1597).
    sendingRef.current = true
    setIsSending(true)
    streamingRef.current = true

    const baseline = messages.length
    let sessionId = currentSessionId
    let answer = ''
    let aiId = ''
    let aiStarted = false
    // Whether the server acknowledged the question (its `user_message` event is
    // emitted only after the question is checkpointed). An abort before it
    // means the server never stored the turn.
    let accepted = false
    let userMessage: NotebookChatMessage | null = null

    // A new turn cancels any previous one still in flight.
    abortControllerRef.current?.abort()
    const controller = new AbortController()
    abortControllerRef.current = controller
    const isActive = () => abortControllerRef.current === controller

    // The answer bubble is created on the first token so an empty bubble never
    // flashes; a refetch that dropped it is repaired instead of losing tokens.
    const bubble = (content: string): NotebookChatMessage => ({
      id: aiId,
      type: 'ai',
      content,
      timestamp: new Date().toISOString()
    })
    const renderAnswer = (content: string) => {
      answer = content
      if (!aiStarted) {
        aiStarted = true
        aiId = `ai-${Date.now()}`
        setMessages(prev => [...prev, bubble(content)])
        return
      }
      setMessages(prev => (
        prev.some(msg => msg.id === aiId)
          ? prev.map(msg => msg.id === aiId ? { ...msg, content } : msg)
          : [...prev, bubble(content)]
      ))
    }

    try {
      // Auto-create session if none exists
      if (!sessionId) {
        try {
          const defaultTitle = message.length > 30
            ? `${message.substring(0, 30)}...`
            : message
          const newSession = await chatApi.createSession({
            notebook_id: notebookId,
            title: defaultTitle,
            // Include pending model override when creating session
            model_override: pendingModelOverride ?? undefined
          })
          sessionId = newSession.id
          setCurrentSessionId(sessionId)
          // Clear pending model override now that it's applied to the session
          setPendingModelOverride(null)
          queryClient.invalidateQueries({
            queryKey: QUERY_KEYS.notebookChatSessions(notebookId)
          })
        } catch (err: unknown) {
          const error = err as { response?: { data?: { detail?: string } }, message?: string };
          toast.error(getApiErrorMessage(error.response?.data?.detail || error.message, (key) => t(key), 'apiErrors.failedToCreateSession'))
          return false
        }
      }

      // Add user message optimistically
      const pending: NotebookChatMessage = {
        id: `temp-${Date.now()}`,
        type: 'human',
        content: message,
        timestamp: new Date().toISOString()
      }
      userMessage = pending
      setMessages(prev => [...prev, pending])

      // Build context and send message
      const context = await buildContext()
      const body = await chatApi.sendMessageStream({
        session_id: sessionId,
        message,
        context,
        model_override: modelOverride ?? (currentSession?.model_override ?? undefined)
      }, controller.signal)

      const reader = body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        // Keep the last incomplete line for the next read.
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          const jsonStr = line.slice(6).trim()
          if (!jsonStr) continue

          let event: { type: string, content?: string, message?: string, code?: string }
          try {
            event = JSON.parse(jsonStr)
          } catch {
            console.error('Error parsing SSE data:', line)
            continue
          }

          if (event.type === 'user_message') {
            // The server echoes only after checkpointing the question, so this
            // is the acknowledgement an abort can rely on.
            accepted = true
          } else if (event.type === 'token') {
            renderAnswer(answer + (event.content || ''))
          } else if (event.type === 'complete') {
            // The server sends the cleaned text (thinking stripped) and has
            // persisted it — adopt it instead of the raw stream.
            if (event.content !== undefined) {
              renderAnswer(event.content)
            }
          } else if (event.type === 'error') {
            throw new ChatStreamError(0, event.message, event.code)
          }
        }
      }

      // Pick up the persisted messages (server ids, cleaned content).
      await refetchCurrentSession()
      return true
    } catch (err: unknown) {
      const aborted = controller.signal.aborted
      const error = err as { status?: number, message?: string, code?: string }

      if (aborted) {
        if (!accepted) {
          // The acknowledgement can have been in flight when the abort landed,
          // and the server may have stored the question already. Ask before
          // restoring it, or the retry leaves a duplicate turn behind.
          if (sessionId) {
            const reconciled = await reconciledAbort(sessionId, baseline, message)
            if (reconciled) {
              queryClient.setQueryData(QUERY_KEYS.notebookChatSession(sessionId), reconciled)
              if (isActive()) setMessages(reconciled.messages)
              return true
            }
          }
          // Stopped before the server stored the question: drop the optimistic
          // copy and let the composer keep the typed text. Any answer bubble is
          // from an older stream.
          if (userMessage) {
            const droppedId = userMessage.id
            setMessages(prev => prev.filter(msg => msg.id !== droppedId))
          }
          return false
        }
        // Stop: the server persists the partial answer, so wait for the
        // cancellation handler to settle instead of racing it with a refetch.
        if (sessionId) {
          // Only wait for what the turn can actually produce: the question,
          // plus an answer if one had started.
          const settled = await waitForSettlement(
            sessionId,
            baseline + (aiStarted ? 2 : 1)
          )
          if (settled) {
            queryClient.setQueryData(QUERY_KEYS.notebookChatSession(sessionId), settled)
            if (isActive()) {
              preserveMessagesAfterSendRef.current = true
              setMessages(settled.messages)
            }
          }
        }
        // The turn itself succeeded: the question was accepted and kept.
        return true
      }

      if (error instanceof ChatStreamError && error.status === 401) {
        // The axios interceptor does this for every other API call.
        if (typeof window !== 'undefined') {
          localStorage.removeItem('auth-storage')
          window.location.href = '/login'
        }
      } else {
        console.error('Error sending message:', error)
        // Endpoint-authored errors carry a code, so their text can be
        // translated; anything else is the backend's reason or the fallback.
        const key = error.code ? STREAM_ERROR_KEYS[error.code] : undefined
        toast.error(key ? t(key) : getApiErrorMessage(error.message, (k) => t(k), 'apiErrors.failedToSendMessage'))
        // Remove the optimistic message on failure. A partial answer, if any,
        // is in the checkpoint and comes back with the refetch.
        setMessages(prev => prev.filter(msg => !msg.id.startsWith('temp-')))
      }
      await refetchCurrentSession()
      return false
    } finally {
      // Scoped to this turn: a send made after a Stop owns the state now.
      if (isActive()) {
        abortControllerRef.current = null
        streamingRef.current = false
        sendingRef.current = false
        setIsSending(false)
      }
    }
  }, [
    notebookId,
    currentSessionId,
    currentSession,
    messages.length,
    pendingModelOverride,
    buildContext,
    refetchCurrentSession,
    queryClient,
    waitForSettlement,
    reconciledAbort,
    t
  ])

  // Stop the in-flight answer. Generation is cancelled server-side and the
  // partial answer is kept; the aborted send resyncs once the server settles.
  // `isSending` stays on until that resync finishes, so the session switcher
  // cannot move to another thread while the stopped one is still landing.
  const stopStreaming = useCallback(() => {
    abortControllerRef.current?.abort()
  }, [])

  // Switch session
  const switchSession = useCallback((sessionId: string) => {
    setCurrentSessionId(sessionId)
  }, [])

  // Create session
  const createSession = useCallback((title?: string) => {
    return createSessionMutation.mutate({
      notebook_id: notebookId,
      title
    })
  }, [createSessionMutation, notebookId])

  // Update session
  const updateSession = useCallback((sessionId: string, data: UpdateNotebookChatSessionRequest) => {
    return updateSessionMutation.mutate({
      sessionId,
      data
    })
  }, [updateSessionMutation])

  // Delete session
  const deleteSession = useCallback((sessionId: string) => {
    return deleteSessionMutation.mutate(sessionId)
  }, [deleteSessionMutation])

  // Set model override - handles both existing sessions and pending state
  const setModelOverride = useCallback((model: string | null) => {
    if (currentSessionId) {
      // Session exists - update it directly
      updateSessionMutation.mutate({
        sessionId: currentSessionId,
        data: { model_override: model }
      })
    } else {
      // No session yet - store as pending
      setPendingModelOverride(model)
    }
  }, [currentSessionId, updateSessionMutation])

  // Abort an in-flight turn when the component unmounts
  useEffect(() => {
    return () => {
      abortControllerRef.current?.abort()
    }
  }, [])

  // Update token/char counts when context selections change
  useEffect(() => {
    const updateContextCounts = async () => {
      try {
        await buildContext()
      } catch (error) {
        console.error('Error updating context counts:', error)
      }
    }
    updateContextCounts()
  }, [buildContext])

  return {
    // State
    sessions,
    currentSession: currentSession || sessions.find(s => s.id === currentSessionId),
    currentSessionId,
    messages,
    isSending,
    loadingSessions,
    tokenCount,
    charCount,
    pendingModelOverride,

    // Actions
    createSession,
    updateSession,
    deleteSession,
    switchSession,
    sendMessage,
    stopStreaming,
    setModelOverride,
    refetchSessions
  }
}
