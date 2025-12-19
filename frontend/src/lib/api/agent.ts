/**
 * Agent API Client
 */

import { apiClient } from './client'
import { getApiUrl } from '../config'
import type {
  AgentExecuteRequest,
  AgentExecuteResponse,
  AgentModelsResponse,
  AgentToolsResponse,
  AgentStreamEvent,
} from '../types/agent'

export const agentApi = {
  /**
   * Execute agent with a message (non-streaming)
   */
  async execute(request: AgentExecuteRequest): Promise<AgentExecuteResponse> {
    const response = await apiClient.post<AgentExecuteResponse>(
      '/agent/execute',
      { ...request, stream: false }
    )
    return response.data
  },

  /**
   * Stream agent execution
   * Returns an async generator that yields stream events
   */
  async *stream(request: AgentExecuteRequest): AsyncGenerator<AgentStreamEvent> {
    // Get API URL dynamically
    const apiUrl = await getApiUrl()
    
    // Get auth token from localStorage
    let authHeader: Record<string, string> = {}
    if (typeof window !== 'undefined') {
      const authStorage = localStorage.getItem('auth-storage')
      if (authStorage) {
        try {
          const { state } = JSON.parse(authStorage)
          if (state?.token) {
            authHeader = { 'Authorization': `Bearer ${state.token}` }
          }
        } catch {
          // Ignore parse errors
        }
      }
    }
    
    const response = await fetch(`${apiUrl}/api/agent/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...authHeader,
      },
      body: JSON.stringify({ ...request, stream: true }),
    })

    if (!response.ok) {
      throw new Error(`Agent stream failed: ${response.statusText}`)
    }

    const reader = response.body?.getReader()
    if (!reader) {
      throw new Error('No response body')
    }

    const decoder = new TextDecoder()
    let buffer = ''

    try {
      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6).trim()
            if (data) {
              try {
                const event: AgentStreamEvent = JSON.parse(data)
                yield event
                if (event.type === 'done' || event.type === 'error') {
                  return
                }
              } catch {
                console.warn('Failed to parse SSE event:', data)
              }
            }
          }
        }
      }
    } finally {
      reader.releaseLock()
    }
  },

  /**
   * Get list of supported models
   */
  async getModels(): Promise<AgentModelsResponse> {
    const response = await apiClient.get<AgentModelsResponse>('/agent/models')
    return response.data
  },

  /**
   * Get list of available tools
   */
  async getTools(): Promise<AgentToolsResponse> {
    const response = await apiClient.get<AgentToolsResponse>('/agent/tools')
    return response.data
  },
}
