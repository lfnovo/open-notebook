import { apiClient } from './client'

export interface Workspace {
  id: string
  name: string
  description?: string
  visibility: 'private' | 'shared' | 'community'
  owner_id: string
  org_id?: string
  created: string
  updated: string
}

export interface WorkspaceMember {
  id: string
  workspace_id: string
  user_id: string
  role: 'viewer' | 'editor' | 'owner'
  created: string
  updated: string
}

export const workspacesApi = {
  list: () => apiClient.get<Workspace[]>('/workspaces'),
  get: (id: string) => apiClient.get<Workspace>(`/workspaces/${id}`),
  create: (data: { name: string; description?: string; visibility?: string }) =>
    apiClient.post<Workspace>('/workspaces', data),
  update: (id: string, data: Partial<Workspace>) =>
    apiClient.put<Workspace>(`/workspaces/${id}`, data),
  delete: (id: string) => apiClient.delete(`/workspaces/${id}`),
  getMembers: (id: string) => apiClient.get<WorkspaceMember[]>(`/workspaces/${id}/members`),
  inviteMember: (id: string, data: { user_id: string; role: string }) =>
    apiClient.post<WorkspaceMember>(`/workspaces/${id}/members`, data),
  removeMember: (id: string, memberId: string) =>
    apiClient.delete(`/workspaces/${id}/members/${memberId}`),
}
