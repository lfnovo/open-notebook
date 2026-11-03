import apiClient from './client'
import { SectionDeleteResponse, SectionResponse } from '@/lib/types/api'

export const sectionsApi = {
  list: async () => {
    const response = await apiClient.get<SectionResponse[]>('/sections')
    return response.data
  },

  create: async (name: string) => {
    const response = await apiClient.post<SectionResponse>('/sections', { name })
    return response.data
  },

  rename: async (id: string, name: string) => {
    const response = await apiClient.put<SectionResponse>(`/sections/${id}`, { name })
    return response.data
  },

  delete: async (id: string) => {
    const response = await apiClient.delete<SectionDeleteResponse>(`/sections/${id}`)
    return response.data
  },
}
