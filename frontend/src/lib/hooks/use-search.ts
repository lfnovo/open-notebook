import { useMutation } from '@tanstack/react-query'
import { toast } from 'sonner'
import { useTranslation } from '@/lib/hooks/use-translation'
import { getApiErrorKey } from '@/lib/utils/error-handler'
import { searchApi } from '@/lib/api/search'
import { SearchRequest } from '@/lib/types/search'

export function useSearch() {
  const { t } = useTranslation()
  return useMutation({
    mutationFn: async (params: SearchRequest) => {
      const response = await searchApi.search(params)

      // Process results to add final_score
      const processedResults = response.results.map(result => ({
        ...result,
        final_score: result.relevance ?? result.similarity ?? result.score ?? 0
      }))

      // Sort by final_score descending
      processedResults.sort((a, b) => b.final_score - a.final_score)

      return {
        ...response,
        results: processedResults
      }
    },
    onError: (error: Error) => {
      toast.error(t('apiErrors.searchFailed'), {
        description: t(getApiErrorKey(error.message))
      })
    }
  })
}
