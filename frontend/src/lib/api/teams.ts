import apiClient from './client'

export type TeamRole = 'owner' | 'admin' | 'member' | 'viewer'
export type TeamMemberStatus = 'active' | 'disabled'

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

export interface TeamCreateRequest {
  name: string
  slug?: string
}

export interface TeamUpdateRequest {
  name?: string
}

export interface TeamMemberUser {
  id: string
  username: string
  display_name?: string | null
  email?: string | null
}

export interface TeamMember {
  id: string
  team: string
  user: string
  user_info?: TeamMemberUser | null
  role: TeamRole
  status: TeamMemberStatus | 'invited'
  created: string
  updated?: string | null
}

export interface TeamMemberUpsertRequest {
  user_id: string
  role: TeamRole
  status?: TeamMemberStatus
}

export const teamsApi = {
  list: async (params?: { q?: string; limit?: number; offset?: number }) => {
    const response = await apiClient.get<TeamListResponse>('/teams', { params })
    return response.data
  },

  create: async (data: TeamCreateRequest) => {
    const response = await apiClient.post<Team>('/teams', data)
    return response.data
  },

  update: async (teamId: string, data: TeamUpdateRequest) => {
    const response = await apiClient.patch<Team>(`/teams/${teamId}`, data)
    return response.data
  },

  delete: async (teamId: string) => {
    await apiClient.delete(`/teams/${teamId}`)
  },

  listMembers: async (teamId: string) => {
    const response = await apiClient.get<TeamMember[]>(`/teams/${teamId}/members`)
    return response.data
  },

  upsertMember: async (teamId: string, data: TeamMemberUpsertRequest) => {
    const response = await apiClient.post<TeamMember>(`/teams/${teamId}/members`, data)
    return response.data
  },

  removeMember: async (teamId: string, userId: string) => {
    await apiClient.delete(`/teams/${teamId}/members/${userId}`)
  },
}
