// 'use client'

// import { useState, useCallback, useEffect } from 'react'
// import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
// import { toast } from 'sonner'
// import { getApiErrorMessage } from '@/lib/utils/error-handler'
// import { useTranslation } from '@/lib/hooks/use-translation'
// import { chatApi } from '@/lib/api/chat'
// import { QUERY_KEYS } from '@/lib/api/query-client'
// import {
//   NotebookChatMessage,
//   CreateNotebookChatSessionRequest,
//   UpdateNotebookChatSessionRequest,
//   SourceListResponse,
//   NoteResponse
// } from '@/lib/types/api'
// import { ContextSelections } from '@/app/(dashboard)/notebooks/[id]/page'

// interface UseNotebookChatParams {
//   notebookId: string
//   sources: SourceListResponse[]
//   notes: NoteResponse[]
//   contextSelections: ContextSelections
// }

// export function useNotebookChat({ notebookId, sources, notes, contextSelections }: UseNotebookChatParams) {
//   const { t } = useTranslation()
//   const queryClient = useQueryClient()
//   const [currentSessionId, setCurrentSessionId] = useState<string | null>(null)
//   const [messages, setMessages] = useState<NotebookChatMessage[]>([])
//   const [isSending, setIsSending] = useState(false)
//   const [tokenCount, setTokenCount] = useState<number>(0)
//   const [charCount, setCharCount] = useState<number>(0)
//   // Pending model override for when user changes model before a session exists
//   const [pendingModelOverride, setPendingModelOverride] = useState<string | null>(null)
//   // Suggested follow-up questions
//   const [suggestedQuestions, setSuggestedQuestions] = useState<string[]>([])

//   // Fetch sessions for this notebook
//   const {
//     data: sessions = [],
//     isLoading: loadingSessions,
//     refetch: refetchSessions
//   } = useQuery({
//     queryKey: QUERY_KEYS.notebookChatSessions(notebookId),
//     queryFn: () => chatApi.listSessions(notebookId),
//     enabled: !!notebookId
//   })

//   // Fetch current session with messages
//   const {
//     data: currentSession,
//     // refetch: refetchCurrentSession
//   } = useQuery({
//     queryKey: QUERY_KEYS.notebookChatSession(currentSessionId!),
//     queryFn: () => chatApi.getSession(currentSessionId!),
//     enabled: !!notebookId && !!currentSessionId
//   })

//   // Update messages when current session changes
//   useEffect(() => {
//     if (currentSession?.messages) {
//       console.log('📬 [Hook] Current session loaded with messages:', currentSession.messages.length)

//       setMessages(prevMessages => {
//         const serverMessages = currentSession.messages || []

//         // Keep optimistic messages that are not already represented in the server payload.
//         const optimisticMessages = prevMessages.filter(optimistic => {
//           if (optimistic.id.startsWith('temp-') || optimistic.id.startsWith('ai-')) {
//             return !serverMessages.some(server =>
//               server.type === optimistic.type &&
//               server.content.trim() === optimistic.content.trim() &&
//               Math.abs(new Date(server.timestamp).getTime() - new Date(optimistic.timestamp).getTime()) < 30000
//             )
//           }
//           return true
//         })

//         // Combine and deduplicate by ID (prefer server messages over optimistic)
//         const merged = [...serverMessages, ...optimisticMessages]
//         const seenIds = new Set<string>()
//         const deduplicated = merged.filter(msg => {
//           if (seenIds.has(msg.id)) {
//             console.warn(`🔴 Duplicate message ID detected: ${msg.id}`)
//             return false
//           }
//           seenIds.add(msg.id)
//           return true
//         })

//         return deduplicated
//       })
//     }

//     // ✅ Load persisted suggested questions when session loads
//     if (currentSession?.suggested_questions && currentSession.suggested_questions.length > 0) {
//       console.log('💡 [Hook] Loading persisted suggestions from session:', currentSession.suggested_questions)
//       setSuggestedQuestions(currentSession.suggested_questions)
//     } else {
//       console.log('⚠️ [Hook] No suggestions in current session')
//       setSuggestedQuestions([])
//     }
//   }, [currentSession])

//   // Auto-select most recent session when sessions are loaded
//   useEffect(() => {
//     if (sessions.length > 0 && !currentSessionId) {
//       // Sessions are sorted by created date desc from API
//       const mostRecentSession = sessions[0]
//       setCurrentSessionId(mostRecentSession.id)
//     }
//   }, [sessions, currentSessionId])

//   // Create session mutation
//   const createSessionMutation = useMutation({
//     mutationFn: (data: CreateNotebookChatSessionRequest) =>
//       chatApi.createSession(data),
//     onSuccess: (newSession) => {
//       queryClient.invalidateQueries({
//         queryKey: QUERY_KEYS.notebookChatSessions(notebookId)
//       })
//       setCurrentSessionId(newSession.id)
//       toast.success(t.chat.sessionCreated)
//     },
//     onError: (err: unknown) => {
//       const error = err as { response?: { data?: { detail?: string } }, message?: string };
//       toast.error(getApiErrorMessage(error.response?.data?.detail || error.message, (key) => t(key), 'apiErrors.failedToCreateSession'))
//     }
//   })

//   // Update session mutation
//   const updateSessionMutation = useMutation({
//     mutationFn: ({ sessionId, data }: {
//       sessionId: string
//       data: UpdateNotebookChatSessionRequest
//     }) => chatApi.updateSession(sessionId, data),
//     onSuccess: () => {
//       queryClient.invalidateQueries({
//         queryKey: QUERY_KEYS.notebookChatSessions(notebookId)
//       })
//       queryClient.invalidateQueries({
//         queryKey: QUERY_KEYS.notebookChatSession(currentSessionId!)
//       })
//       toast.success(t.chat.sessionUpdated)
//     },
//     onError: (err: unknown) => {
//       const error = err as { response?: { data?: { detail?: string } }, message?: string };
//       toast.error(getApiErrorMessage(error.response?.data?.detail || error.message, (key) => t(key), 'apiErrors.failedToUpdateSession'))
//     }
//   })

//   // Delete session mutation
//   const deleteSessionMutation = useMutation({
//     mutationFn: (sessionId: string) =>
//       chatApi.deleteSession(sessionId),
//     onSuccess: (_, deletedId) => {
//       queryClient.invalidateQueries({
//         queryKey: QUERY_KEYS.notebookChatSessions(notebookId)
//       })
//       if (currentSessionId === deletedId) {
//         setCurrentSessionId(null)
//         setMessages([])
//       }
//       toast.success(t.chat.sessionDeleted)
//     },
//     onError: (err: unknown) => {
//       const error = err as { response?: { data?: { detail?: string } }, message?: string };
//       toast.error(getApiErrorMessage(error.response?.data?.detail || error.message, (key) => t(key), 'apiErrors.failedToDeleteSession'))
//     }
//   })

//   // Build context from sources and notes based on user selections
//   const buildContext = useCallback(async () => {
//     // Build context_config mapping IDs to selection modes
//     const context_config: { sources: Record<string, string>, notes: Record<string, string> } = {
//       sources: {},
//       notes: {}
//     }

//     // Map source selections
//     sources.forEach(source => {
//       const mode = contextSelections.sources[source.id]
//       if (mode === 'insights') {
//         context_config.sources[source.id] = 'insights'
//       } else if (mode === 'full') {
//         context_config.sources[source.id] = 'full content'
//       } else {
//         context_config.sources[source.id] = 'not in'
//       }
//     })

//     // Map note selections
//     notes.forEach(note => {
//       const mode = contextSelections.notes[note.id]
//       if (mode === 'full') {
//         context_config.notes[note.id] = 'full content'
//       } else {
//         context_config.notes[note.id] = 'not in'
//       }
//     })

//     // Call API to build context with actual content
//     const response = await chatApi.buildContext({
//       notebook_id: notebookId,
//       context_config
//     })

//     // Store token and char counts
//     setTokenCount(response.token_count)
//     setCharCount(response.char_count)

//     return response.context
//   }, [notebookId, sources, notes, contextSelections])

//   // Send message (synchronous, no streaming)
//   const sendMessage = useCallback(async (message: string, modelOverride?: string) => {
//     let sessionId = currentSessionId

//     // Auto-create session if none exists
//     if (!sessionId) {
//       try {
//         const defaultTitle = message.length > 30
//           ? `${message.substring(0, 30)}...`
//           : message
//         const newSession = await chatApi.createSession({
//           notebook_id: notebookId,
//           title: defaultTitle,
//           // Include pending model override when creating session
//           model_override: pendingModelOverride ?? undefined
//         })
//         sessionId = newSession.id
//         setCurrentSessionId(sessionId)
//         // Clear pending model override now that it's applied to the session
//         setPendingModelOverride(null)
//         queryClient.invalidateQueries({
//           queryKey: QUERY_KEYS.notebookChatSessions(notebookId)
//         })
//       } catch (err: unknown) {
//         const error = err as { response?: { data?: { detail?: string } }, message?: string };
//         toast.error(getApiErrorMessage(error.response?.data?.detail || error.message, (key) => t(key), 'apiErrors.failedToCreateSession'))
//         return
//       }
//     }

//     // Add user message optimistically
//     const userMessage: NotebookChatMessage = {
//       id: `temp-${Date.now()}`,
//       type: 'human',
//       content: message,
//       timestamp: new Date().toISOString()
//     }
//     setMessages(prev => [...prev, userMessage])
//     setIsSending(true)
//     // Clear previous suggested questions when sending new message
//     setSuggestedQuestions([])

//     // Create AI message placeholder
//     const aiMessageId = `ai-${Date.now()}`
//     const aiMessage: NotebookChatMessage = {
//       id: aiMessageId,
//       type: 'ai',
//       content: '',
//       timestamp: new Date().toISOString()
//     }
//     setMessages(prev => [...prev, aiMessage])

//     try {
//       // Build context and send message
//       const context = await buildContext()

//       // Use streaming API with token callback and suggested questions callback
//       await chatApi.sendMessageStream({
//         session_id: sessionId,
//         message,
//         context,
//         model_override: modelOverride ?? (currentSession?.model_override ?? undefined)
//       }, (token) => {
//         // Update AI message content with streamed token
//         setMessages(prev => {
//           const newMessages = [...prev]
//           const msgIndex = newMessages.findIndex(m => m.id === aiMessageId)
//           if (msgIndex >= 0) {
//             const currentMsg = newMessages[msgIndex]
//             newMessages[msgIndex] = {
//               ...currentMsg,
//               content: currentMsg.content + token
//             }
//           }
//           return newMessages
//         })
//       }, (questions) => {
//         // Handle suggested questions from stream
//         console.log('💡 [Hook] Received suggested questions from stream:', questions)
//         setSuggestedQuestions(questions)
//       })

//       // Refetch current session to get updated data
//       console.log('🔄 [Hook] Refetching session after stream completes...')
//       const updatedSession = await refetchCurrentSession()

//       // Load persisted suggestions from session after refetch
//       if (updatedSession?.data?.suggested_questions) {
//         console.log('💾 [Hook] Loaded persisted suggestions from session:', updatedSession.data.suggested_questions)
//         setSuggestedQuestions(updatedSession.data.suggested_questions)
//       }
//     } catch (err: unknown) {
//       const error = err as { response?: { data?: { detail?: string } }, message?: string };
//       console.error('Error sending message:', error)
//       toast.error(getApiErrorMessage(error.response?.data?.detail || error.message, (key) => t(key), 'apiErrors.failedToSendMessage'))
//       // Remove optimistic messages on error
//       setMessages(prev => prev.filter(msg => !msg.id.startsWith('temp-') && msg.id !== aiMessageId))
//     } finally {
//       setIsSending(false)
//     }
//   }, [
//     notebookId,
//     currentSessionId,
//     currentSession,
//     pendingModelOverride,
//     buildContext,
//     // refetchCurrentSession,
//     queryClient,
//     t
//   ])

//   // Switch session
//   const switchSession = useCallback((sessionId: string) => {
//     setCurrentSessionId(sessionId)
//   }, [])

//   // Create session
//   const createSession = useCallback((title?: string) => {
//     return createSessionMutation.mutate({
//       notebook_id: notebookId,
//       title
//     })
//   }, [createSessionMutation, notebookId])

//   // Update session
//   const updateSession = useCallback((sessionId: string, data: UpdateNotebookChatSessionRequest) => {
//     return updateSessionMutation.mutate({
//       sessionId,
//       data
//     })
//   }, [updateSessionMutation])

//   // Delete session
//   const deleteSession = useCallback((sessionId: string) => {
//     return deleteSessionMutation.mutate(sessionId)
//   }, [deleteSessionMutation])

//   // Set model override - handles both existing sessions and pending state
//   const setModelOverride = useCallback((model: string | null) => {
//     if (currentSessionId) {
//       // Session exists - update it directly
//       updateSessionMutation.mutate({
//         sessionId: currentSessionId,
//         data: { model_override: model }
//       })
//     } else {
//       // No session yet - store as pending
//       setPendingModelOverride(model)
//     }
//   }, [currentSessionId, updateSessionMutation])

//   // Update token/char counts when context selections change
//   useEffect(() => {
//     const updateContextCounts = async () => {
//       try {
//         await buildContext()
//       } catch (error) {
//         console.error('Error updating context counts:', error)
//       }
//     }
//     updateContextCounts()
//   }, [buildContext])

//   return {
//     // State
//     sessions,
//     currentSession: currentSession || sessions.find(s => s.id === currentSessionId),
//     currentSessionId,
//     messages,
//     isSending,
//     loadingSessions,
//     tokenCount,
//     charCount,
//     pendingModelOverride,
//     suggestedQuestions,

//     // Actions
//     createSession,
//     updateSession,
//     deleteSession,
//     switchSession,
//     sendMessage,
//     setModelOverride,
//   }
// }




'use client'

import { useState, useCallback, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { getApiErrorMessage } from '@/lib/utils/error-handler'
import { useTranslation } from '@/lib/hooks/use-translation'
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
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null)
  const [messages, setMessages] = useState<NotebookChatMessage[]>([])
  const [isSending, setIsSending] = useState(false)
  const [tokenCount, setTokenCount] = useState<number>(0)
  const [charCount, setCharCount] = useState<number>(0)
  const [pendingModelOverride, setPendingModelOverride] = useState<string | null>(null)
  const [suggestedQuestions, setSuggestedQuestions] = useState<string[]>([])

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
    // If no session is selected, clear messages
    if (!currentSessionId) {
      setMessages([])
      setSuggestedQuestions([])
      return
    }

    if (currentSession?.messages) {
      setMessages(prevMessages => {
        const serverMessages = currentSession.messages || []

        const optimisticMessages = prevMessages.filter(optimistic => {
          if (optimistic.id.startsWith('temp-') || optimistic.id.startsWith('ai-')) {
            return !serverMessages.some(server =>
              server.type === optimistic.type &&
              server.content.trim() === optimistic.content.trim() &&
              Math.abs(new Date(server.timestamp).getTime() - new Date(optimistic.timestamp).getTime()) < 30000
            )
          }
          return true
        })

        const merged = [...serverMessages, ...optimisticMessages]
        const seenIds = new Set<string>()
        const deduplicated = merged.filter(msg => {
          if (seenIds.has(msg.id)) return false
          seenIds.add(msg.id)
          return true
        })

        return deduplicated
      })
    }

    // ✅ FIX: Only load suggested questions from session when NOT actively sending
    // This prevents overwriting questions already set by the stream callback
    if (!isSending) {
      if (currentSession?.suggested_questions && currentSession.suggested_questions.length > 0) {
        setSuggestedQuestions(currentSession.suggested_questions)
      } else {
        setSuggestedQuestions([])
      }
    }
  }, [currentSession, currentSessionId]) // watch both so clearing works on session deselect

  // Auto-select most recent session only on initial load (when no session is active)
  // Do NOT auto-select after deletion — let the UI stay empty so user can choose
  useEffect(() => {
    if (sessions.length > 0 && currentSessionId === null) {
      // Only auto-select on first load (messages is empty = fresh load, not post-delete)
      if (messages.length === 0) {
        const mostRecentSession = sessions[0]
        setCurrentSessionId(mostRecentSession.id)
      }
    }
  }, [sessions]) // eslint-disable-line react-hooks/exhaustive-deps

  // Create session mutation
  const createSessionMutation = useMutation({
    mutationFn: (data: CreateNotebookChatSessionRequest) =>
      chatApi.createSession(data),
    onSuccess: (newSession) => {
      queryClient.invalidateQueries({
        queryKey: QUERY_KEYS.notebookChatSessions(notebookId)
      })
      setCurrentSessionId(newSession.id)
      toast.success(t.chat.sessionCreated)
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
      toast.success(t.chat.sessionUpdated)
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
      // Remove the deleted session from cache immediately so its useEffect doesn't re-populate messages
      queryClient.removeQueries({
        queryKey: QUERY_KEYS.notebookChatSession(deletedId)
      })
      queryClient.invalidateQueries({
        queryKey: QUERY_KEYS.notebookChatSessions(notebookId)
      })
      if (currentSessionId === deletedId) {
        setCurrentSessionId(null)
        setMessages([])
        setSuggestedQuestions([])
      }
      toast.success(t.chat.sessionDeleted)
    },
    onError: (err: unknown) => {
      const error = err as { response?: { data?: { detail?: string } }, message?: string };
      toast.error(getApiErrorMessage(error.response?.data?.detail || error.message, (key) => t(key), 'apiErrors.failedToDeleteSession'))
    }
  })

  // Build context from sources and notes based on user selections
  const buildContext = useCallback(async () => {
    const context_config: { sources: Record<string, string>, notes: Record<string, string> } = {
      sources: {},
      notes: {}
    }

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

    notes.forEach(note => {
      const mode = contextSelections.notes[note.id]
      if (mode === 'full') {
        context_config.notes[note.id] = 'full content'
      } else {
        context_config.notes[note.id] = 'not in'
      }
    })

    const response = await chatApi.buildContext({
      notebook_id: notebookId,
      context_config
    })

    setTokenCount(response.token_count)
    setCharCount(response.char_count)

    return response.context
  }, [notebookId, sources, notes, contextSelections])

  // Send message (with streaming)
  const sendMessage = useCallback(async (message: string, modelOverride?: string) => {
    let sessionId = currentSessionId

    if (!sessionId) {
      try {
        const defaultTitle = message.length > 30
          ? `${message.substring(0, 30)}...`
          : message
        const newSession = await chatApi.createSession({
          notebook_id: notebookId,
          title: defaultTitle,
          model_override: pendingModelOverride ?? undefined
        })
        sessionId = newSession.id
        setCurrentSessionId(sessionId)
        setPendingModelOverride(null)
        queryClient.invalidateQueries({
          queryKey: QUERY_KEYS.notebookChatSessions(notebookId)
        })
      } catch (err: unknown) {
        const error = err as { response?: { data?: { detail?: string } }, message?: string };
        toast.error(getApiErrorMessage(error.response?.data?.detail || error.message, (key) => t(key), 'apiErrors.failedToCreateSession'))
        return
      }
    }

    const userMessage: NotebookChatMessage = {
      id: `temp-${Date.now()}`,
      type: 'human',
      content: message,
      timestamp: new Date().toISOString()
    }
    setMessages(prev => [...prev, userMessage])
    setIsSending(true)

    // ✅ FIX: Clear suggestions only once here, before streaming starts
    setSuggestedQuestions([])

    const aiMessageId = `ai-${Date.now()}`
    const aiMessage: NotebookChatMessage = {
      id: aiMessageId,
      type: 'ai',
      content: '',
      timestamp: new Date().toISOString()
    }
    setMessages(prev => [...prev, aiMessage])

    try {
      const context = await buildContext()

      await chatApi.sendMessageStream({
        session_id: sessionId,
        message,
        context,
        model_override: modelOverride ?? (currentSession?.model_override ?? undefined)
      }, (token) => {
        setMessages(prev => {
          const newMessages = [...prev]
          const msgIndex = newMessages.findIndex(m => m.id === aiMessageId)
          if (msgIndex >= 0) {
            const currentMsg = newMessages[msgIndex]
            newMessages[msgIndex] = {
              ...currentMsg,
              content: currentMsg.content + token
            }
          }
          return newMessages
        })
      }, (questions) => {
        // ✅ FIX: Set suggested questions ONLY here from stream — single source of truth
        setSuggestedQuestions(questions)
      })

      // ✅ FIX: After streaming completes, refetch and clear optimistic placeholder
      const result = await refetchCurrentSession()
      
      // Remove the optimistic placeholder and keep only server messages
      if (result?.data?.messages) {
        setMessages(result.data.messages)
      }

    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } }, message?: string };
      console.error('Error sending message:', error)
      toast.error(getApiErrorMessage(error.response?.data?.detail || error.message, (key) => t(key), 'apiErrors.failedToSendMessage'))
      setMessages(prev => prev.filter(msg => !msg.id.startsWith('temp-') && msg.id !== aiMessageId))
    } finally {
      setIsSending(false)
    }
  }, [
    notebookId,
    currentSessionId,
    currentSession,
    pendingModelOverride,
    buildContext,
    refetchCurrentSession,
    queryClient,
    t
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

  // Set model override
  const setModelOverride = useCallback((model: string | null) => {
    if (currentSessionId) {
      updateSessionMutation.mutate({
        sessionId: currentSessionId,
        data: { model_override: model }
      })
    } else {
      setPendingModelOverride(model)
    }
  }, [currentSessionId, updateSessionMutation])

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
    sessions,
    currentSession: currentSession || sessions.find(s => s.id === currentSessionId),
    currentSessionId,
    messages,
    isSending,
    loadingSessions,
    tokenCount,
    charCount,
    pendingModelOverride,
    suggestedQuestions,
    createSession,
    updateSession,
    deleteSession,
    switchSession,
    sendMessage,
    setModelOverride,
  }
}