import apiClient from './client'

export type UserRole = 'admin' | 'user'
export type UserStatus = 'active' | 'disabled'

export interface UserListItem {
  id: string
  username: string
  email?: string | null
  display_name?: string | null
  role: UserRole
  status: UserStatus
  created: string
  updated: string
  last_login_at?: string | null
  source_count: number
  notebook_count: number
}

export interface UserListResponse {
  items: UserListItem[]
  total: number
  limit: number
  offset: number
}

export const usersApi = {
  list: async (params?: {
    q?: string
    role?: UserRole
    status?: UserStatus
    limit?: number
    offset?: number
  }) => {
    const response = await apiClient.get<UserListResponse>('/users', { params })
    return response.data
  },
}
