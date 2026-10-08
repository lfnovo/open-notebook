import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { chatQuizzesApi } from '@/lib/api/chat-quizzes'
import { QUERY_KEYS } from '@/lib/api/query-client'
import type { ExamAnswers } from '@/lib/types/exams'
import { useToast } from './use-toast'
import { useTranslation } from './use-translation'
import { getApiErrorMessage } from '@/lib/utils/error-handler'

export function useChatQuiz(id: string) {
  return useQuery({ queryKey: QUERY_KEYS.chatQuiz(id), queryFn: () => chatQuizzesApi.get(id), enabled: !!id, retry: false })
}

export function useSubmitChatQuiz(id: string) {
  const client = useQueryClient()
  const { toast } = useToast()
  const { t } = useTranslation()
  return useMutation({
    mutationFn: (answers: ExamAnswers) => chatQuizzesApi.submit(id, answers),
    retry: false,
    onSuccess: (data) => client.setQueryData(QUERY_KEYS.chatQuiz(id), data),
    onError: (error) => toast({ title: t('common.error'), description: getApiErrorMessage(error, key => t(key)), variant: 'destructive' }),
  })
}
