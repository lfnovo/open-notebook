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

export interface WorkspaceResourceMoveRequest {
  resource_type: 'notebook'
  resource_id: string
  mode?: 'move'
}

export interface WorkspaceResourceMoveResponse {
  resource_type: string
  resource_id: string
  source_workspace_id?: string | null
  target_workspace_id: string
  mode: 'move'
  message: string
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

  moveResource: async (workspaceId: string, data: WorkspaceResourceMoveRequest) => {
    const response = await apiClient.post<WorkspaceResourceMoveResponse>(
      `/workspaces/${workspaceId}/resources/move`,
      data
    )
    return response.data
  },
}
