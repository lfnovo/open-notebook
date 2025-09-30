import apiClient from './client'

export interface EmbedContentRequest {
  item_id: string
  item_type: 'source' | 'note'
}

export interface EmbedContentResponse {
  success: boolean
  message: string
  chunks_created?: number
}

export const embeddingApi = {
  embedContent: async (itemId: string, itemType: 'source' | 'note'): Promise<EmbedContentResponse> => {
    const response = await apiClient.post<EmbedContentResponse>('/embed', {
      item_id: itemId,
      item_type: itemType
    })
    return response.data
  }
}