import axios from 'axios'
import { apiClient } from './client'
import { getApiUrl } from '@/lib/config'

export interface MindMapNode {
  label: string
  children?: MindMapNode[]
}

export interface MindMapResponse {
  mind_map: MindMapNode
  source_id: string
}

export interface MindMapRequest {
  model_name?: string
  temperature?: number
}

// Dedicated axios instance for mindmap — no timeout since LLM generation can take many minutes
const mindmapClient = axios.create({
  timeout: 0, // no timeout
  headers: { 'Content-Type': 'application/json' },
  withCredentials: false,
})

// Reuse the same request interceptor logic (base URL + auth)
mindmapClient.interceptors.request.use(async (config) => {
  // Always re-resolve the API URL so it picks up the correct host (works on any IP)
  const apiUrl = await getApiUrl()
  config.baseURL = `${apiUrl}/api`

  if (typeof window !== 'undefined') {
    const authStorage = localStorage.getItem('auth-storage')
    if (authStorage) {
      try {
        const { state } = JSON.parse(authStorage)
        if (state?.token) {
          config.headers.Authorization = `Bearer ${state.token}`
        }
      } catch (_) {}
    }
  }
  return config
})

export const mindmapApi = {
  generate: async (sourceId: string, options: MindMapRequest = {}): Promise<MindMapResponse> => {
    const response = await mindmapClient.post<MindMapResponse>(
      `/sources/${encodeURIComponent(sourceId)}/mindmap`,
      { model_name: 'qwen3', temperature: 0.2, ...options }
    )
    return response.data
  },

  getImages: async (sourceId: string): Promise<{ images: string[]; count: number }> => {
    const response = await mindmapClient.get<{ images: string[]; source_id: string; count: number }>(
      `/sources/${encodeURIComponent(sourceId)}/images`
    )
    return response.data
  },

  getNodeSummary: async (sourceId: string, nodeName: string, rootSubject: string): Promise<{ summary: string; node_name: string; root_subject: string }> => {
    const response = await mindmapClient.post(
      `/sources/${encodeURIComponent(sourceId)}/node-summary`,
      { node_name: nodeName, root_subject: rootSubject }
    )
    return response.data
  },

  getSourceSummary: async (sourceId: string): Promise<{ summary: string; source_id: string }> => {
    const response = await mindmapClient.post(
      `/sources/${encodeURIComponent(sourceId)}/summary`,
      {}
    )
    return response.data
  },

  // Poll source status to show live progress messages
  getStatus: async (sourceId: string): Promise<{ status: string | null; message?: string }> => {
    try {
      const response = await apiClient.get(`/sources/${encodeURIComponent(sourceId)}/status`)
      return response.data
    } catch {
      return { status: null }
    }
  },
}
