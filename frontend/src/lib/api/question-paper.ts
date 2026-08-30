import apiClient from './client'
import type {
  BookUploadResponse,
  GeneratePaperRequest,
  GeneratePaperResponse,
  GenerateBankBatchRequest,
  GenerateBankBatchResponse,
  BankBatchStatusResponse,
  BankBatchResultResponse,
  BankBatchSummary,
  PaperResult,
  PaperStatusResponse,
  PaperSummary,
  BankQuestion,
  LibraryBook,
  RegenerateMissingResponse,
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

  regenerateMissing: async (paperId: string): Promise<RegenerateMissingResponse> => {
    const response = await apiClient.post<RegenerateMissingResponse>(
      `/papers/${paperId}/regenerate-missing`
    )
    return response.data
  },

  generateBankBatch: async (
    request: GenerateBankBatchRequest,
  ): Promise<GenerateBankBatchResponse> => {
    const response = await apiClient.post<GenerateBankBatchResponse>(
      '/papers/bank/batch/generate',
      request,
    )
    return response.data
  },

  getBankBatchStatus: async (batchId: string): Promise<BankBatchStatusResponse> => {
    const response = await apiClient.get<BankBatchStatusResponse>(
      `/papers/bank/batch/${encodeURIComponent(batchId)}/status`,
    )
    return response.data
  },

  getBankBatchResult: async (batchId: string): Promise<BankBatchResultResponse> => {
    const response = await apiClient.get<BankBatchResultResponse>(
      `/papers/bank/batch/${encodeURIComponent(batchId)}/result`,
    )
    return response.data
  },

  listBankBatches: async (): Promise<BankBatchSummary[]> => {
    const response = await apiClient.get<BankBatchSummary[]>('/papers/bank/batches')
    return response.data
  },

  searchBank: async (query: string = '', limit: number = 1000): Promise<BankQuestion[]> => {
    const response = await apiClient.get<BankQuestion[]>('/papers/bank/search', {
      params: { q: query, limit },
    })
    return response.data
  },

  exportBankXlsx: async (questionIds: string[]): Promise<Blob> => {
    const response = await apiClient.post(
      '/papers/bank/export/xlsx',
      { question_ids: questionIds },
      { responseType: 'blob' },
    )
    return response.data
  },

  listBooks: async (): Promise<LibraryBook[]> => {
    const response = await apiClient.get<LibraryBook[]>('/papers/books')
    return response.data
  },

  getBook: async (bookId: string): Promise<LibraryBook> => {
    const response = await apiClient.get<LibraryBook>(
      `/papers/books/${encodeURIComponent(bookId)}`,
    )
    return response.data
  },

  deleteBankQuestion: async (questionId: string): Promise<void> => {
    await apiClient.delete(`/papers/bank/${questionId}`)
  },

  uploadBook: async (payload: {
    file: File
    book_name: string
    year: string
    grade: string
    subject?: string
    edition?: string
    display_name?: string
  }): Promise<LibraryBook> => {
    const formData = new FormData()
    formData.append('file', payload.file)
    formData.append('book_name', payload.book_name)
    formData.append('year', payload.year)
    formData.append('grade', payload.grade)
    formData.append('subject', payload.subject || '')
    formData.append('edition', payload.edition || '')
    formData.append('display_name', payload.display_name || '')
    const response = await apiClient.post<LibraryBook>('/papers/books/upload', formData)
    return response.data
  },

  deleteBook: async (bookId: string): Promise<void> => {
    await apiClient.delete(`/papers/books/${bookId}`)
  },

  updateBook: async (
    bookId: string,
    payload: {
      book_name: string
      year: string
      grade: string
      subject?: string
      edition?: string
      display_name?: string
    },
  ): Promise<LibraryBook> => {
    const response = await apiClient.patch<LibraryBook>(
      `/papers/books/${encodeURIComponent(bookId)}`,
      payload,
    )
    return response.data
  },

  exportXlsx: async (paperId: string): Promise<Blob> => {
    const response = await apiClient.get(`/papers/${paperId}/export/xlsx`, { responseType: 'blob' })
    return response.data
  },

  exportDocx: async (paperId: string): Promise<Blob> => {
    const response = await apiClient.get(`/papers/${paperId}/export/docx`, { responseType: 'blob' })
    return response.data
  },

  exportTxt: async (paperId: string): Promise<Blob> => {
    const response = await apiClient.get(`/papers/${paperId}/export/txt`, { responseType: 'blob' })
    return response.data
  },
}
