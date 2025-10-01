'use client'

import { useState, useCallback, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { chatApi } from '@/lib/api/chat'
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

export function useNotebookChat({ notebookId, sources, notes, contextSelections }: UseNotebookChatParams) {
  const queryClient = useQueryClient()
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null)
  const [messages, setMessages] = useState<NotebookChatMessage[]>([])
  const [isSending, setIsSending] = useState(false)

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

  // Update messages when current session changes
  useEffect(() => {
    if (currentSession?.messages) {
      setMessages(currentSession.messages)
    }
  }, [currentSession])

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
      toast.success('Chat session created')
    },
    onError: () => {
      toast.error('Failed to create chat session')
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
      toast.success('Session updated')
    },
    onError: () => {
      toast.error('Failed to update session')
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
      toast.success('Session deleted')
    },
    onError: () => {
      toast.error('Failed to delete session')
    }
  })

  // Build context from sources and notes based on user selections
  const buildContext = useCallback(() => {
    return {
      sources: sources
        .filter(source => {
          const mode = contextSelections.sources[source.id]
          return mode && mode !== 'off' // Include if mode is 'insights' or 'full'
        })
        .map(source => {
          const mode = contextSelections.sources[source.id]
          return {
            id: source.id,
            content: mode === 'insights' ? 'insights' : 'full content'
          }
        }),
      notes: notes
        .filter(note => {
          const mode = contextSelections.notes[note.id]
          return mode && mode !== 'off' // Include if mode is 'full' (notes only have off/full)
        })
        .map(note => ({
          id: note.id,
          content: 'full content' // Notes always use full content when included
        }))
    }
  }, [sources, notes, contextSelections])

  // Send message (synchronous, no streaming)
  const sendMessage = useCallback(async (message: string, modelOverride?: string) => {
    let sessionId = currentSessionId

    // Auto-create session if none exists
    if (!sessionId) {
      try {
        const defaultTitle = message.length > 30
          ? `${message.substring(0, 30)}...`
          : message
        const newSession = await chatApi.createSession({
          notebook_id: notebookId,
          title: defaultTitle
        })
        sessionId = newSession.id
        setCurrentSessionId(sessionId)
        queryClient.invalidateQueries({
          queryKey: QUERY_KEYS.notebookChatSessions(notebookId)
        })
      } catch {
        toast.error('Failed to create chat session')
        return
      }
    }

    // Add user message optimistically
    const userMessage: NotebookChatMessage = {
      id: `temp-${Date.now()}`,
      type: 'human',
      content: message,
      timestamp: new Date().toISOString()
    }
    setMessages(prev => [...prev, userMessage])
    setIsSending(true)

    try {
      // Build context and send message
      const context = buildContext()
      const response = await chatApi.sendMessage({
        session_id: sessionId,
        message,
        context,
        model_override: modelOverride ?? (currentSession?.model_override ?? undefined)
      })

      // Update messages with API response
      setMessages(response.messages)

      // Refetch current session to get updated data
      await refetchCurrentSession()
    } catch (error) {
      console.error('Error sending message:', error)
      toast.error('Failed to send message')
      // Remove optimistic message on error
      setMessages(prev => prev.filter(msg => !msg.id.startsWith('temp-')))
    } finally {
      setIsSending(false)
    }
  }, [
    notebookId,
    currentSessionId,
    currentSession,
    buildContext,
    refetchCurrentSession,
    queryClient
  ])

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

  return {
    // State
    sessions,
    currentSession: currentSession || sessions.find(s => s.id === currentSessionId),
    currentSessionId,
    messages,
    isSending,
    loadingSessions,

    // Actions
    createSession,
    updateSession,
    deleteSession,
    switchSession,
    sendMessage,
    refetchSessions
  }
}
