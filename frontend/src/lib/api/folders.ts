import apiClient from './client'
import { FolderDeleteResponse, FolderResponse } from '@/lib/types/api'

export const foldersApi = {
  list: async () => {
    const response = await apiClient.get<FolderResponse[]>('/folders')
    return response.data
  },

  /** `sectionId`: omit/undefined = none (create) or unchanged (rename); null = no section. */
  create: async (name: string, sectionId?: string | null) => {
    const response = await apiClient.post<FolderResponse>('/folders', {
      name,
      ...(sectionId ? { section_id: sectionId } : {}),
    })
    return response.data
  },

  rename: async (id: string, name: string, sectionId?: string | null) => {
    const response = await apiClient.put<FolderResponse>(`/folders/${id}`, {
      name,
      ...(sectionId !== undefined ? { section_id: sectionId } : {}),
    })
    return response.data
  },

  delete: async (id: string) => {
    const response = await apiClient.delete<FolderDeleteResponse>(`/folders/${id}`)
    return response.data
  },
}
