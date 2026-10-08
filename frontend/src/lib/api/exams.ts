import apiClient from './client'
import { CreateExamRequest, Exam, ExamAnswers, ExamAttempt } from '@/lib/types/exams'

export const examsApi = {
  list: async (notebookId?: string) => {
    const response = await apiClient.get<Exam[]>('/exams', {
      params: notebookId ? { notebook_id: notebookId } : undefined,
    })
    return response.data
  },

  get: async (id: string, includeAnswers = false) => {
    const response = await apiClient.get<Exam>(`/exams/${encodeURIComponent(id)}`, {
      params: { include_answers: includeAnswers },
    })
    return response.data
  },

  create: async (data: CreateExamRequest) => {
    const response = await apiClient.post<Exam>('/exams', data)
    return response.data
  },

  delete: async (id: string) => {
    await apiClient.delete(`/exams/${encodeURIComponent(id)}`)
  },

  listAttempts: async (examId: string) => {
    const response = await apiClient.get<ExamAttempt[]>(`/exams/${encodeURIComponent(examId)}/attempts`)
    return response.data
  },

  submitAttempt: async (examId: string, answers: ExamAnswers) => {
    const response = await apiClient.post<ExamAttempt>(
      `/exams/${encodeURIComponent(examId)}/attempts`,
      { answers }
    )
    return response.data
  },

  deleteAttempt: async (attemptId: string) => {
    await apiClient.delete(`/exam-attempts/${encodeURIComponent(attemptId)}`)
  },
}
