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

export interface UserCreateRequest {
  username: string
  email?: string
  display_name?: string
  role?: UserRole
  password?: string
}

export interface UserCreateResponse extends UserListItem {
  temporary_password?: string | null
}

export interface UserUpdateRequest {
  display_name?: string
  role?: UserRole
  status?: UserStatus
}

export interface ResetUserPasswordResponse {
  success: boolean
  temporary_password: string
  message: string
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

  create: async (data: UserCreateRequest) => {
    const response = await apiClient.post<UserCreateResponse>('/users', data)
    return response.data
  },

  update: async (userId: string, data: UserUpdateRequest) => {
    const response = await apiClient.patch<UserListItem>(`/users/${userId}`, data)
    return response.data
  },

  resetPassword: async (userId: string) => {
    const response = await apiClient.post<ResetUserPasswordResponse>(`/users/${userId}/reset-password`)
    return response.data
  },
}
