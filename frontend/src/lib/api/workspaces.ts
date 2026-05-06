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

export interface WorkspacePermissionPolicy {
  member_can_read: boolean
  member_can_create_source: boolean
  member_can_update_own_source: boolean
  member_can_process_own_source: boolean
  member_can_delete_own_source: boolean
  member_can_remove_source: boolean
  member_can_create_note: boolean
  member_can_update_own_note: boolean
  member_can_delete_own_note: boolean
  member_can_delete_chat: boolean
  member_can_update_notebook: boolean
}

export interface WorkspacePolicyResponse {
  workspace_id: string
  policy: WorkspacePermissionPolicy
  effective_policy: WorkspacePermissionPolicy
}

export interface WorkspaceSystemPolicyResponse {
  policy: WorkspacePermissionPolicy
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

  getPolicy: async (workspaceId: string) => {
    const response = await apiClient.get<WorkspacePolicyResponse>(
      `/workspaces/${workspaceId}/policy`
    )
    return response.data
  },

  updatePolicy: async (workspaceId: string, data: WorkspacePermissionPolicy) => {
    const response = await apiClient.patch<WorkspacePolicyResponse>(
      `/workspaces/${workspaceId}/policy`,
      data
    )
    return response.data
  },

  getSystemPolicy: async () => {
    const response = await apiClient.get<WorkspaceSystemPolicyResponse>(
      '/workspaces/system-policy'
    )
    return response.data
  },

  updateSystemPolicy: async (data: WorkspacePermissionPolicy) => {
    const response = await apiClient.patch<WorkspaceSystemPolicyResponse>(
      '/workspaces/system-policy',
      data
    )
    return response.data
  },
}
