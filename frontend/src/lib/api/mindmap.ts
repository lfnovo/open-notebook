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

/* -------------------------------------------------- */
/* 🔥 NORMALIZE ANY RESPONSE FORMAT */
/* -------------------------------------------------- */
function normalizeMindMap(data: any): MindMapResponse {
  // case 1: already correct
  if (data?.mind_map?.label) {
    return data
  }

  // case 2: backend returned direct node
  if (data?.label) {
    return {
      mind_map: data,
      source_id: data.source_id || 'unknown',
    }
  }

  // case 3: string JSON from LLM
  if (typeof data === 'string') {
    try {
      const parsed = JSON.parse(data)
      return normalizeMindMap(parsed)
    } catch {}
  }

  // case 4: wrapped response
  if (data?.data?.label) {
    return {
      mind_map: data.data,
      source_id: data.source_id || 'unknown',
    }
  }

  console.error('Invalid mindmap response:', data)
  throw new Error('Invalid mindmap structure')
}

/* -------------------------------------------------- */

const mindmapClient = axios.create({
  timeout: 0,
  headers: { 'Content-Type': 'application/json' },
  withCredentials: false,
})

mindmapClient.interceptors.request.use(async (config) => {
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
      } catch {}
    }
  }

  return config
})

export const mindmapApi = {
  /* ---------------- GENERATE ---------------- */
  generate: async (
    sourceId: string,
    options: MindMapRequest = {}
  ): Promise<MindMapResponse> => {

    const response = await mindmapClient.post(
      `/sources/${encodeURIComponent(sourceId)}/mindmap`,
      { model_name: 'qwen3', temperature: 0.2, ...options }
    )

    // ✅ IMPORTANT FIX
    return normalizeMindMap(response.data)
  },

  /* ---------------- IMAGES ---------------- */
  getImages: async (sourceId: string) => {
    const response = await mindmapClient.get(
      `/sources/${encodeURIComponent(sourceId)}/images`
    )
    return response.data
  },

  /* ---------------- NODE SUMMARY ---------------- */
  getNodeSummary: async (
    sourceId: string,
    nodeName: string,
    rootSubject: string
  ) => {
    const response = await mindmapClient.post(
      `/sources/${encodeURIComponent(sourceId)}/node-summary`,
      { node_name: nodeName, root_subject: rootSubject }
    )
    return response.data
  },

  /* ---------------- SOURCE SUMMARY ---------------- */
  getSourceSummary: async (sourceId: string) => {
    const response = await mindmapClient.post(
      `/sources/${encodeURIComponent(sourceId)}/summary`,
      {}
    )
    return response.data
  },

  /* ---------------- STATUS ---------------- */
  getStatus: async (sourceId: string) => {
    try {
      const response = await apiClient.get(
        `/sources/${encodeURIComponent(sourceId)}/status`
      )
      return response.data
    } catch {
      return { status: null }
    }
  },
}