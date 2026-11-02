import apiClient from './client'
import { FolderDeleteResponse, FolderResponse } from '@/lib/types/api'

export const foldersApi = {
  list: async () => {
    const response = await apiClient.get<FolderResponse[]>('/folders')
    return response.data
  },

  create: async (name: string) => {
    const response = await apiClient.post<FolderResponse>('/folders', { name })
    return response.data
  },

  rename: async (id: string, name: string) => {
    const response = await apiClient.put<FolderResponse>(`/folders/${id}`, { name })
    return response.data
  },

  delete: async (id: string) => {
    const response = await apiClient.delete<FolderDeleteResponse>(`/folders/${id}`)
    return response.data
  },
}
