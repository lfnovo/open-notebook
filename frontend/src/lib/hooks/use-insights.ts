import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { insightsApi } from '@/lib/api/insights'
import { QUERY_KEYS } from '@/lib/api/query-client'
import { useToast } from '@/lib/hooks/use-toast'
import { useTranslation } from '@/lib/hooks/use-translation'
import { getApiErrorKey } from '@/lib/utils/error-handler'

export function useInsight(id: string, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: ['insights', id],
    queryFn: () => insightsApi.get(id),
    enabled: options?.enabled !== false && !!id,
    staleTime: 30 * 1000, // 30 seconds
  })
}

export function useSaveInsightAsNote() {
  const queryClient = useQueryClient()
  const { toast } = useToast()
  const { t } = useTranslation()

  return useMutation({
    mutationFn: ({ insightId, notebookId }: { insightId: string; notebookId: string }) =>
      insightsApi.saveAsNote(insightId, notebookId),
    onSuccess: (_, { notebookId }) => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.notes(notebookId) })
      toast({
        title: t('common.success'),
        description: t('sources.insightSavedAsNote'),
      })
    },
    onError: (error: unknown) => {
      toast({
        title: t('common.error'),
        description: t(getApiErrorKey(error, 'sources.failedToSaveInsightAsNote')),
        variant: 'destructive',
      })
    },
  })
}
