import { useMutation } from '@tanstack/react-query'

import { discoverApi } from '@/lib/api/discover'
import { useToast } from '@/lib/hooks/use-toast'
import { useTranslation } from '@/lib/hooks/use-translation'
import { getApiErrorKey } from '@/lib/utils/error-handler'
import type {
  DiscoverSourcesRequest,
  DiscoverSourcesResponse,
} from '@/lib/types/discover'

export function useDiscoverSources() {
  const { toast } = useToast()
  const { t } = useTranslation()

  return useMutation<DiscoverSourcesResponse, unknown, DiscoverSourcesRequest>({
    mutationFn: (input) => discoverApi.discoverSources(input),
    onSuccess: (data) => {
      toast({
        title: t('common.success'),
        description: t('discover.summary', {
          created: data.created_count,
          skipped: data.skipped_count,
        }),
      })
    },
    onError: (error: unknown) => {
      toast({
        title: t('common.error'),
        description: t(getApiErrorKey(error, t('common.error'))),
        variant: 'destructive',
      })
    },
  })
}
