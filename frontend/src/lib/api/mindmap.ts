import { apiClient } from './client'

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

export const mindmapApi = {
  generate: async (sourceId: string, options: MindMapRequest = {}): Promise<MindMapResponse> => {
    const response = await apiClient.post<MindMapResponse>(
      `/sources/${sourceId}/mindmap`,
      { model_name: 'qwen3', temperature: 0.2, ...options }
    )
    return response.data
  },
}
