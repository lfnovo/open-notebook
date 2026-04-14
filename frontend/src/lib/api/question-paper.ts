import apiClient from './client'
import type {
  BookUploadResponse,
  GeneratePaperRequest,
  GeneratePaperResponse,
  PaperResult,
  PaperStatusResponse,
  PaperSummary,
  BankQuestion,
} from '@/lib/types/question-paper'

export const questionPaperApi = {
  generatePaper: async (request: GeneratePaperRequest): Promise<GeneratePaperResponse> => {
    const response = await apiClient.post<GeneratePaperResponse>('/papers/generate', request)
    return response.data
  },

  listPapers: async (): Promise<PaperSummary[]> => {
    const response = await apiClient.get<PaperSummary[]>('/papers')
    return response.data
  },

  getPaperStatus: async (paperId: string): Promise<PaperStatusResponse> => {
    const response = await apiClient.get<PaperStatusResponse>(`/papers/${paperId}/status`)
    return response.data
  },

  getPaperResult: async (paperId: string): Promise<PaperResult> => {
    const response = await apiClient.get<PaperResult>(`/papers/${paperId}/result`)
    return response.data
  },

  deletePaper: async (paperId: string): Promise<void> => {
    await apiClient.delete(`/papers/${paperId}`)
  },

  searchBank: async (query: string = '', limit: number = 20): Promise<BankQuestion[]> => {
    const response = await apiClient.get<BankQuestion[]>('/papers/bank/search', {
      params: { q: query, limit },
    })
    return response.data
  },

  deleteBankQuestion: async (questionId: string): Promise<void> => {
    await apiClient.delete(`/papers/bank/${questionId}`)
  },

  uploadBook: async (file: File): Promise<BookUploadResponse> => {
    const formData = new FormData()
    formData.append('file', file)
    const response = await apiClient.post<BookUploadResponse>('/papers/books/upload', formData)
    return response.data
  },

  deleteBook: async (bookId: string): Promise<void> => {
    await apiClient.delete(`/papers/books/${bookId}`)
  },
}
