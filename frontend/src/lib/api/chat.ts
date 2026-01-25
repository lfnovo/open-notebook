import apiClient from './client'
import {
  ModuleChatSession,
  ModuleChatSessionWithMessages,
  CreateModuleChatSessionRequest,
  UpdateModuleChatSessionRequest,
  SendModuleChatMessageRequest,
  ModuleChatMessage,
  BuildContextRequest,
  BuildContextResponse,
} from '@/lib/types/api'

export const chatApi = {
  // Session management
  listSessions: async (moduleId: string) => {
    const response = await apiClient.get<ModuleChatSession[]>(
      `/chat/sessions`,
      { params: { module_id: moduleId } }
    )
    return response.data
  },

  createSession: async (data: CreateModuleChatSessionRequest) => {
    const response = await apiClient.post<ModuleChatSession>(
      `/chat/sessions`,
      data
    )
    return response.data
  },

  getSession: async (sessionId: string) => {
    const response = await apiClient.get<ModuleChatSessionWithMessages>(
      `/chat/sessions/${sessionId}`
    )
    return response.data
  },

  updateSession: async (sessionId: string, data: UpdateModuleChatSessionRequest) => {
    const response = await apiClient.put<ModuleChatSession>(
      `/chat/sessions/${sessionId}`,
      data
    )
    return response.data
  },

  deleteSession: async (sessionId: string) => {
    await apiClient.delete(`/chat/sessions/${sessionId}`)
  },

  // Messaging (synchronous, no streaming)
  sendMessage: async (data: SendModuleChatMessageRequest) => {
    const response = await apiClient.post<{
      session_id: string
      messages: ModuleChatMessage[]
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
}

export default chatApi
