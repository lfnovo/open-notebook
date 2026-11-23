import apiClient from './client'
import { getAuthToken } from '@/lib/auth-token'
import {
  NotebookChatSession,
  NotebookChatSessionWithMessages,
  CreateNotebookChatSessionRequest,
  UpdateNotebookChatSessionRequest,
  SendNotebookChatMessageRequest,
  NotebookChatMessage,
  BuildContextRequest,
  BuildContextResponse,
} from '@/lib/types/api'

/** Non-2xx answer from the streaming endpoint, with the backend's reason. */
export class ChatStreamError extends Error {
  status: number

  constructor(status: number, detail?: string) {
    // No generic text: callers fall back to a translated key when detail is
    // empty, exactly like the axios-based calls do.
    super(detail || '')
    this.name = 'ChatStreamError'
    this.status = status
  }
}

export const chatApi = {
  // Session management
  listSessions: async (notebookId: string) => {
    const response = await apiClient.get<NotebookChatSession[]>(
      `/chat/sessions`,
      { params: { notebook_id: notebookId } }
    )
    return response.data
  },

  createSession: async (data: CreateNotebookChatSessionRequest) => {
    const response = await apiClient.post<NotebookChatSession>(
      `/chat/sessions`,
      data
    )
    return response.data
  },

  getSession: async (sessionId: string) => {
    const response = await apiClient.get<NotebookChatSessionWithMessages>(
      `/chat/sessions/${sessionId}`
    )
    return response.data
  },

  updateSession: async (sessionId: string, data: UpdateNotebookChatSessionRequest) => {
    const response = await apiClient.put<NotebookChatSession>(
      `/chat/sessions/${sessionId}`,
      data
    )
    return response.data
  },

  deleteSession: async (sessionId: string) => {
    await apiClient.delete(`/chat/sessions/${sessionId}`)
  },

  // Messaging (synchronous, no streaming)
  sendMessage: async (data: SendNotebookChatMessageRequest) => {
    const response = await apiClient.post<{
      session_id: string
      messages: NotebookChatMessage[]
    }>(
      `/chat/execute`,
      data
    )
    return response.data
  },

  buildContext: async (data: BuildContextRequest) => {
    const response = await apiClient.post<BuildContextResponse>(
      `/chat/context`,
      data
    )
    return response.data
  },

  /**
   * Streaming variant of `sendMessage`.
   *
   * Uses the dedicated route handler (not the rewrite proxy, which gzips the
   * response to completion) and returns the raw SSE body for the caller to
   * parse. `signal` cancels the request, which stops server-side generation.
   */
  sendMessageStream: async (
    data: SendNotebookChatMessageRequest,
    signal?: AbortSignal
  ) => {
    const token = getAuthToken()

    const response = await fetch('/api/chat/execute/stream', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token && { Authorization: `Bearer ${token}` }),
      },
      body: JSON.stringify(data),
      signal,
    })

    if (!response.ok) {
      // Prefer the backend's reason ("Session not found", …) over a status code.
      let detail: string | undefined
      try {
        const body = await response.json()
        detail = body?.detail || body?.message
      } catch {
        detail = response.statusText || undefined
      }
      throw new ChatStreamError(response.status, detail)
    }

    if (!response.body) {
      throw new ChatStreamError(response.status)
    }

    return response.body
  },
}

export default chatApi
