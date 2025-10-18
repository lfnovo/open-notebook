import apiClient from './client'

export interface EmbedContentRequest {
  item_id: string
  item_type: 'source' | 'note'
  async_processing?: boolean
}

export interface EmbedContentResponse {
  success: boolean
  message: string
  chunks_created?: number
  command_id?: string
}

export interface RebuildEmbeddingsRequest {
  mode: 'existing' | 'all'
  include_sources?: boolean
  include_notes?: boolean
  include_insights?: boolean
}

export interface RebuildEmbeddingsResponse {
  command_id: string
  message: string
  estimated_items: number
}

export interface RebuildProgress {
  total_items?: number
  processed_items?: number
  failed_items?: number
  total?: number
  processed?: number
  percentage?: number
}

export interface RebuildStats {
  sources_processed?: number
  notes_processed?: number
  insights_processed?: number
  sources?: number
  notes?: number
  insights?: number
  failed?: number
  failed_items?: number
  processing_time?: number
}

export interface RebuildStatusResponse {
  command_id: string
  status: 'queued' | 'running' | 'completed' | 'failed'
  progress?: RebuildProgress
  stats?: RebuildStats
  started_at?: string
  completed_at?: string
  error_message?: string
}

export const embeddingApi = {
  embedContent: async (itemId: string, itemType: 'source' | 'note', asyncProcessing = false): Promise<EmbedContentResponse> => {
    const response = await apiClient.post<EmbedContentResponse>('/embed', {
      item_id: itemId,
      item_type: itemType,
      async_processing: asyncProcessing
    })
    return response.data
  },

  rebuildEmbeddings: async (request: RebuildEmbeddingsRequest): Promise<RebuildEmbeddingsResponse> => {
    const response = await apiClient.post<RebuildEmbeddingsResponse>('/embeddings/rebuild', request)
    return response.data
  },

  getRebuildStatus: async (commandId: string): Promise<RebuildStatusResponse> => {
    const response = await apiClient.get<RebuildStatusResponse>(`/embeddings/rebuild/${commandId}/status`)
    return response.data
  }
}
