import apiClient from './client'
import { NoteResponse, CreateNoteRequest, UpdateNoteRequest } from '@/lib/types/api'

export const notesApi = {
  list: async (params?: { notebook_id?: string }) => {
    const response = await apiClient.get<NoteResponse[]>('/notes', { params })
    return response.data
  },

  get: async (id: string) => {
    const response = await apiClient.get<NoteResponse>(`/notes/${id}`)
    return response.data
  },

  create: async (data: CreateNoteRequest) => {
    const response = await apiClient.post<NoteResponse>('/notes', data)
    return response.data
  },

  update: async (id: string, data: UpdateNoteRequest) => {
    const response = await apiClient.put<NoteResponse>(`/notes/${id}`, data)
    return response.data
  },

  delete: async (id: string) => {
    await apiClient.delete(`/notes/${id}`)
  }
}