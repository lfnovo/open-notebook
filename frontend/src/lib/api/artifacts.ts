import apiClient from './client'
import type {
  Artifact,
  GenerateArtifactRequest,
  GenerateArtifactResponse,
} from '@/lib/types/artifacts'

export const artifactsApi = {
  generateArtifact: async (input: GenerateArtifactRequest) => {
    const response = await apiClient.post<GenerateArtifactResponse>(
      '/artifacts',
      input
    )
    return response.data
  },

  listArtifacts: async (notebookId?: string) => {
    const response = await apiClient.get<Artifact[]>('/artifacts', {
      params: notebookId ? { notebook_id: notebookId } : undefined,
    })
    return response.data
  },

  getArtifact: async (artifactId: string) => {
    const response = await apiClient.get<Artifact>(`/artifacts/${artifactId}`)
    return response.data
  },

  deleteArtifact: async (artifactId: string) => {
    const response = await apiClient.delete(`/artifacts/${artifactId}`)
    return response.data
  },
}
