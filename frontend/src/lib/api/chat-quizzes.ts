import apiClient from './client'
import type { ExamAnswers, ExamAttempt, ExamQuestion } from '@/lib/types/exams'
import type { ChatImage } from '@/lib/types/api'

export interface ChatQuizDetail {
  id: string
  title: string
  questions: ExamQuestion[]
  images: Record<string, ChatImage>
  latest_attempt: ExamAttempt | null
  review_questions: ExamQuestion[] | null
}

export const chatQuizzesApi = {
  get: async (id: string) => (await apiClient.get<ChatQuizDetail>(`/chat-quizzes/${encodeURIComponent(id)}`)).data,
  submit: async (id: string, answers: ExamAnswers) => (await apiClient.post<ChatQuizDetail>(`/chat-quizzes/${encodeURIComponent(id)}/attempts`, { answers })).data,
}
