import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  ShareGrantCreateRequest,
  ShareResourceType,
  shareGrantsApi,
} from '@/lib/api/share-grants'
import { QUERY_KEYS } from '@/lib/api/query-client'
import { useToast } from '@/lib/hooks/use-toast'
import { useTranslation } from '@/lib/hooks/use-translation'
import { getApiErrorKey } from '@/lib/utils/error-handler'

export function shareGrantKey(resourceType: ShareResourceType, resourceId: string) {
  return ['share-grants', resourceType, resourceId] as const
}

export function useShareGrants(resourceType: ShareResourceType, resourceId?: string) {
  return useQuery({
    queryKey: resourceId ? shareGrantKey(resourceType, resourceId) : ['share-grants', resourceType, 'none'],
    queryFn: () => shareGrantsApi.list(resourceType, resourceId as string),
    enabled: !!resourceId,
  })
}

function invalidateResourceQueries(
  queryClient: ReturnType<typeof useQueryClient>,
  resourceType: ShareResourceType,
  resourceId: string
) {
  queryClient.invalidateQueries({ queryKey: shareGrantKey(resourceType, resourceId) })
  if (resourceType === 'source') {
    queryClient.invalidateQueries({ queryKey: ['sources'] })
    queryClient.invalidateQueries({ queryKey: QUERY_KEYS.source(resourceId) })
    if (typeof window !== 'undefined') {
      window.dispatchEvent(new CustomEvent('sourcesUpdated'))
    }
  } else {
    queryClient.invalidateQueries({ queryKey: QUERY_KEYS.notebooks })
    queryClient.invalidateQueries({ queryKey: QUERY_KEYS.notebook(resourceId) })
  }
}

export function useCreateShareGrant() {
  const queryClient = useQueryClient()
  const { toast } = useToast()
  const { t } = useTranslation()

  return useMutation({
    mutationFn: (data: ShareGrantCreateRequest) => shareGrantsApi.create(data),
    onSuccess: (_, variables) => {
      invalidateResourceQueries(queryClient, variables.resource_type, variables.resource_id)
      toast({ title: t.common.success, description: t.sharing.shareSaved })
    },
    onError: (error: unknown) => {
      toast({
        title: t.common.error,
        description: getApiErrorKey(error, t.common.error),
        variant: 'destructive',
      })
    },
  })
}

export function useDeleteShareGrant(resourceType: ShareResourceType, resourceId: string) {
  const queryClient = useQueryClient()
  const { toast } = useToast()
  const { t } = useTranslation()

  return useMutation({
    mutationFn: (grantId: string) => shareGrantsApi.delete(grantId),
    onSuccess: () => {
      invalidateResourceQueries(queryClient, resourceType, resourceId)
      toast({ title: t.common.success, description: t.sharing.shareRevoked })
    },
    onError: (error: unknown) => {
      toast({
        title: t.common.error,
        description: getApiErrorKey(error, t.common.error),
        variant: 'destructive',
      })
    },
  })
}
