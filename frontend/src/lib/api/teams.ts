import apiClient from './client'

export interface Team {
  id: string
  slug: string
  name: string
  type: 'workspace' | 'system'
  created_by?: string | null
  created: string
  updated: string
  member_count: number
  share_count: number
}

export interface TeamListResponse {
  items: Team[]
  total: number
  limit: number
  offset: number
}

export const teamsApi = {
  list: async () => {
    const response = await apiClient.get<TeamListResponse>('/teams')
    return response.data
  },
}
