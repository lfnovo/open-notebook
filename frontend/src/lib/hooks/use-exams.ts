import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { examsApi } from '@/lib/api/exams'
import { QUERY_KEYS } from '@/lib/api/query-client'
import { useToast } from '@/lib/hooks/use-toast'
import { useTranslation } from '@/lib/hooks/use-translation'
import { getApiErrorMessage } from '@/lib/utils/error-handler'
import { CreateExamRequest, ExamAnswers } from '@/lib/types/exams'

export function useExams(notebookId?: string) {
  return useQuery({
    queryKey: QUERY_KEYS.exams(notebookId),
    queryFn: () => examsApi.list(notebookId),
  })
}

export function useExam(id: string, includeAnswers = false) {
  return useQuery({
    queryKey: QUERY_KEYS.exam(id, includeAnswers),
    queryFn: () => examsApi.get(id, includeAnswers),
    enabled: !!id,
  })
}

export function useExamAttempts(examId: string) {
  return useQuery({
    queryKey: QUERY_KEYS.examAttempts(examId),
    queryFn: () => examsApi.listAttempts(examId),
    enabled: !!examId,
  })
}

function useErrorToast() {
  const { toast } = useToast()
  const { t } = useTranslation()
  return (error: unknown) =>
    toast({
      title: t('common.error'),
      description: getApiErrorMessage(error, (key) => t(key)),
      variant: 'destructive',
    })
}

export function useCreateExam() {
  const queryClient = useQueryClient()
  const { toast } = useToast()
  const { t } = useTranslation()
  const onError = useErrorToast()

  return useMutation({
    mutationFn: (data: CreateExamRequest) => examsApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['exams'] })
      toast({ title: t('common.success'), description: t('exams.createSuccess') })
    },
    onError,
  })
}

export function useDeleteExam() {
  const queryClient = useQueryClient()
  const { toast } = useToast()
  const { t } = useTranslation()
  const onError = useErrorToast()

  return useMutation({
    mutationFn: (id: string) => examsApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['exams'] })
      toast({ title: t('common.success'), description: t('exams.deleteSuccess') })
    },
    onError,
  })
}

export function useSubmitExamAttempt(examId: string) {
  const queryClient = useQueryClient()
  const onError = useErrorToast()

  return useMutation({
    mutationFn: (answers: ExamAnswers) => examsApi.submitAttempt(examId, answers),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['exams'] })
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.examAttempts(examId) })
    },
    onError,
  })
}

export function useDeleteExamAttempt(examId: string) {
  const queryClient = useQueryClient()
  const onError = useErrorToast()

  return useMutation({
    mutationFn: (attemptId: string) => examsApi.deleteAttempt(attemptId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['exams'] })
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.examAttempts(examId) })
    },
    onError,
  })
}
