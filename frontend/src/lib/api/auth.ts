import apiClient from './client'
import { CurrentUserResponse } from '@/lib/types/auth'

export interface ChangePasswordRequest {
  old_password: string
  new_password: string
}

export interface ChangePasswordResponse {
  success: boolean
  message: string
}

export interface ProfileUpdateRequest {
  display_name?: string | null
  locale?: string | null
  theme?: string | null
}

export const authApi = {
  me: async () => {
    const response = await apiClient.get<CurrentUserResponse>('/auth/me')
    return response.data
  },

  updateMe: async (data: ProfileUpdateRequest) => {
    const response = await apiClient.patch<CurrentUserResponse>('/auth/me', data)
    return response.data
  },

  changePassword: async (data: ChangePasswordRequest) => {
    const response = await apiClient.post<ChangePasswordResponse>('/auth/change-password', data)
    return response.data
  },
}
