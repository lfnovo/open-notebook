import apiClient from './client'
import {
  GenerateStudySetRequest,
  ReviewFlashcardResponse,
  SrsRating,
  StudySet,
  StudySetGenerationResponse,
  StudySetListItem,
  StudyJobStatusResponse,
} from '@/lib/types/study'

export const studyApi = {
  generateFlashcards: async (payload: GenerateStudySetRequest) => {
    const response = await apiClient.post<StudySetGenerationResponse>('/study/flashcards', payload)
    return response.data
  },

  generateQuiz: async (payload: GenerateStudySetRequest) => {
    const response = await apiClient.post<StudySetGenerationResponse>('/study/quiz', payload)
    return response.data
  },

  getJobStatus: async (jobId: string) => {
    const response = await apiClient.get<StudyJobStatusResponse>(`/study/jobs/${jobId}`)
    return response.data
  },

  listForNotebook: async (notebookId: string) => {
    const response = await apiClient.get<StudySetListItem[]>(`/notebooks/${notebookId}/study`)
    return response.data
  },

  get: async (studySetId: string) => {
    const response = await apiClient.get<StudySet>(`/study/${studySetId}`)
    return response.data
  },

  delete: async (studySetId: string) => {
    await apiClient.delete(`/study/${studySetId}`)
  },

  reviewFlashcard: async (studySetId: string, itemIndex: number, rating: SrsRating) => {
    const response = await apiClient.post<ReviewFlashcardResponse>(
      `/study/${studySetId}/items/${itemIndex}/review`,
      { rating }
    )
    return response.data
  },
}
