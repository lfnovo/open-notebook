import apiClient from './client'
import type { Model } from '@/lib/types/models'
import type { Transformation } from '@/lib/types/transformations'

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
  current_user_role?: TeamRole | null
  can_manage?: boolean
}

export interface TeamListResponse {
  items: Team[]
  total: number
  limit: number
  offset: number
}

export interface TeamCreateRequest {
  name: string
  owner_id: string
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

export interface TeamAssignableUserListResponse {
  items: TeamMemberUser[]
  total: number
  limit: number
  offset: number
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

export interface TeamModelAllowlistResponse {
  team_id: string
  model_ids: string[]
  models: Model[]
}

export interface TeamTransformationAllowlistResponse {
  team_id: string
  transformation_ids: string[]
  transformations: Transformation[]
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

  listAssignableUsers: async (
    teamId: string,
    params?: { q?: string; limit?: number; offset?: number }
  ) => {
    const response = await apiClient.get<TeamAssignableUserListResponse>(
      `/teams/${teamId}/assignable-users`,
      { params }
    )
    return response.data
  },

  upsertMember: async (teamId: string, data: TeamMemberUpsertRequest) => {
    const response = await apiClient.post<TeamMember>(`/teams/${teamId}/members`, data)
    return response.data
  },

  removeMember: async (teamId: string, userId: string) => {
    await apiClient.delete(`/teams/${teamId}/members/${userId}`)
  },

  listModels: async (teamId: string) => {
    const response = await apiClient.get<TeamModelAllowlistResponse>(`/teams/${teamId}/models`)
    return response.data
  },

  updateModels: async (teamId: string, modelIds: string[]) => {
    const response = await apiClient.put<TeamModelAllowlistResponse>(`/teams/${teamId}/models`, {
      model_ids: modelIds,
    })
    return response.data
  },

  listTransformations: async (teamId: string) => {
    const response = await apiClient.get<TeamTransformationAllowlistResponse>(`/teams/${teamId}/transformations`)
    return response.data
  },

  updateTransformations: async (teamId: string, transformationIds: string[]) => {
    const response = await apiClient.put<TeamTransformationAllowlistResponse>(`/teams/${teamId}/transformations`, {
      transformation_ids: transformationIds,
    })
    return response.data
  },
}
