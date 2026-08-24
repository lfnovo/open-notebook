import { useMutation, useQueries, useQuery, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { questionPaperApi } from '@/lib/api/question-paper'
import type {
  GeneratePaperRequest,
  PaperStatusResponse,
  PaperResult,
} from '@/lib/types/question-paper'

export const QUESTION_PAPER_KEYS = {
  all: ['question-papers'] as const,
  list: () => [...QUESTION_PAPER_KEYS.all, 'list'] as const,
  status: (id: string) => [...QUESTION_PAPER_KEYS.all, 'status', id] as const,
  result: (id: string) => [...QUESTION_PAPER_KEYS.all, 'result', id] as const,
  bank: (q: string) => ['question-bank', q] as const,
  books: ['question-books'] as const,
}

export function usePapers() {
  return useQuery({
    queryKey: QUESTION_PAPER_KEYS.list(),
    queryFn: questionPaperApi.listPapers,
  })
}

export function usePaperStatus(paperId: string | null, enabled: boolean = true) {
  return useQuery<PaperStatusResponse>({
    queryKey: QUESTION_PAPER_KEYS.status(paperId ?? ''),
    queryFn: () => questionPaperApi.getPaperStatus(paperId!),
    enabled: !!paperId && enabled,
    refetchInterval: (query) => {
      const status = query.state.data?.status
      if (status === 'completed' || status === 'failed' || status === 'needs_manual_review') return false
      return 3000 // poll every 3s while running/pending
    },
  })
}

export function usePaperResult(paperId: string | null, enabled: boolean = true) {
  return useQuery<PaperResult>({
    queryKey: QUESTION_PAPER_KEYS.result(paperId ?? ''),
    queryFn: () => questionPaperApi.getPaperResult(paperId!),
    enabled: !!paperId && enabled,
    retry: false,
  })
}

export function useGeneratePaper() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (request: GeneratePaperRequest) => questionPaperApi.generatePaper(request),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUESTION_PAPER_KEYS.list() })
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to start paper generation')
    },
  })
}

export function useDeletePaper() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (paperId: string) => questionPaperApi.deletePaper(paperId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUESTION_PAPER_KEYS.list() })
      toast.success('Paper deleted')
    },
    onError: () => {
      toast.error('Failed to delete paper')
    },
  })
}

export function useBooks() {
  return useQuery({
    queryKey: QUESTION_PAPER_KEYS.books,
    queryFn: questionPaperApi.listBooks,
    staleTime: 30 * 1000,
  })
}

export function useQuestionBank(query: string = '') {
  return useQuery({
    queryKey: QUESTION_PAPER_KEYS.bank(query),
    queryFn: () => questionPaperApi.searchBank(query, 1000),
  })
}

export function useQuestionBooks(bookIds: string[]) {
  const uniqueIds = Array.from(new Set(bookIds.filter(Boolean)))
  const queries = useQueries({
    queries: uniqueIds.map((bookId) => ({
      queryKey: ['question-book', bookId],
      queryFn: () => questionPaperApi.getBook(bookId),
      retry: false,
      staleTime: 5 * 60 * 1000,
    })),
  })
  const titles: Record<string, string> = {}
  uniqueIds.forEach((id, index) => {
    const title = queries[index]?.data?.display_name || queries[index]?.data?.title
    if (title) titles[id] = title
  })
  return titles
}

export function useDeleteBankQuestion() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (questionId: string) => questionPaperApi.deleteBankQuestion(questionId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['question-bank'] })
      toast.success('Question removed from bank')
    },
    onError: () => {
      toast.error('Failed to remove question')
    },
  })
}
