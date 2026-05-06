import apiClient from './client'

export type WorkspaceType = 'personal' | 'team'
export type WorkspaceRole = 'owner' | 'admin' | 'member' | 'viewer'

export interface Workspace {
  id: string
  name: string
  type: WorkspaceType
  owner_id?: string | null
  team_id?: string | null
  created_by?: string | null
  created: string
  updated: string
  current_user_role?: WorkspaceRole | null
  can_manage: boolean
}

export interface WorkspaceListResponse {
  items: Workspace[]
  total: number
}

export const workspacesApi = {
  list: async () => {
    const response = await apiClient.get<WorkspaceListResponse>('/workspaces')
    return response.data
  },

  get: async (workspaceId: string) => {
    const response = await apiClient.get<Workspace>(`/workspaces/${workspaceId}`)
    return response.data
  },
}
