import apiClient from './client'

export type ShareResourceType = 'source' | 'notebook'
export type ShareTargetType = 'user' | 'team'

export const PUBLIC_TEAM_ID = 'team:public'

export interface ShareGrant {
  id: string
  resource_type: ShareResourceType
  resource_id: string
  target_type: ShareTargetType
  target_id: string
  permission: string
  created_by?: string | null
  created: string
}

export interface ShareGrantCreateRequest {
  resource_type: ShareResourceType
  resource_id: string
  target_type: ShareTargetType
  target_id: string
  permission?: 'read'
}

export const shareGrantsApi = {
  list: async (resourceType: ShareResourceType, resourceId: string) => {
    const response = await apiClient.get<ShareGrant[]>('/share-grants', {
      params: { resource_type: resourceType, resource_id: resourceId },
    })
    return response.data
  },

  create: async (data: ShareGrantCreateRequest) => {
    const response = await apiClient.post<ShareGrant>('/share-grants', data)
    return response.data
  },

  delete: async (grantId: string) => {
    await apiClient.delete(`/share-grants/${encodeURIComponent(grantId)}`)
  },
}
