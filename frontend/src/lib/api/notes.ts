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
  },

  /** Create a note from a dropped file; the original is kept on the server. */
  uploadFile: async (notebookId: string, file: File) => {
    const formData = new FormData()
    formData.append('notebook_id', notebookId)
    formData.append('file', file)
    const response = await apiClient.post<NoteResponse>('/notes/upload', formData)
    return response.data
  },

  /** The original file as a Blob (fetched with auth, so it can be previewed or saved). */
  fetchFile: async (id: string) => {
    const response = await apiClient.get<Blob>(`/notes/${id}/file`, { responseType: 'blob' })
    return response.data
  },
}