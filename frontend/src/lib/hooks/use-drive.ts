import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { driveApi } from '@/lib/api/drive'
import { QUERY_KEYS } from '@/lib/api/query-client'
import { useToast } from '@/lib/hooks/use-toast'
import { useTranslation } from '@/lib/hooks/use-translation'
import { getApiErrorMessage } from '@/lib/utils/error-handler'
import { DriveImportRequest } from '@/lib/types/drive'

/** Polled on the Settings page and after the OAuth redirect lands back
 * (?drive=connected / ?drive=error) so the connect/disconnect UI reflects
 * the real backend state rather than optimistic local state. */
export function useDriveStatus() {
  return useQuery({
    queryKey: QUERY_KEYS.driveStatus,
    queryFn: () => driveApi.getStatus(),
    staleTime: 30 * 1000,
  })
}

/**
 * Fetches the Google OAuth consent URL, then does a full-page redirect - this
 * is a standard OAuth flow, not an API call the caller awaits a result from.
 */
export function useConnectDrive() {
  const { toast } = useToast()
  const { t } = useTranslation()

  return useMutation({
    mutationFn: () => driveApi.getAuthUrl(),
    onSuccess: (data) => {
      window.location.href = data.auth_url
    },
    onError: (error: unknown) => {
      toast({
        title: t('common.error'),
        description: getApiErrorMessage(error, (key) => t(key), t('drive.connectFailed')),
        variant: 'destructive',
      })
    },
  })
}

export function useDisconnectDrive() {
  const queryClient = useQueryClient()
  const { toast } = useToast()
  const { t } = useTranslation()

  return useMutation({
    mutationFn: () => driveApi.disconnect(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.driveStatus })
      toast({ title: t('drive.disconnected') })
    },
    onError: (error: unknown) => {
      toast({
        title: t('common.error'),
        description: getApiErrorMessage(error, (key) => t(key), t('drive.disconnectFailed')),
        variant: 'destructive',
      })
    },
  })
}

/**
 * Single-page file list (metadata only). `pageToken` is undefined for the
 * first page; the caller (DriveImportPanel) manages accumulating pages when
 * the user asks for more, mirroring `next_page_token` from Drive's API.
 */
export function useDriveFiles(query: string, pageToken: string | undefined, enabled: boolean) {
  return useQuery({
    queryKey: QUERY_KEYS.driveFiles(query, pageToken),
    queryFn: () => driveApi.listFiles({ query: query || undefined, page_token: pageToken }),
    enabled,
    staleTime: 10 * 1000,
  })
}

export function useImportDriveFile() {
  const queryClient = useQueryClient()
  const { toast } = useToast()
  const { t } = useTranslation()

  return useMutation({
    mutationFn: (data: DriveImportRequest) => driveApi.importFile(data),
    onSuccess: (_, variables) => {
      // Same invalidation shape as useCreateSource() (use-sources.ts) so a
      // Drive import refreshes the sources list exactly like any other
      // add-source method.
      queryClient.invalidateQueries({
        queryKey: QUERY_KEYS.sources(variables.notebook_id),
        refetchType: 'active',
      })
      queryClient.invalidateQueries({
        queryKey: QUERY_KEYS.sourcesInfinite(variables.notebook_id),
        refetchType: 'active',
      })
      queryClient.invalidateQueries({
        queryKey: QUERY_KEYS.sources(),
        refetchType: 'active',
      })
      toast({
        title: t('sources.sourceQueued'),
        description: t('sources.sourceQueuedDesc'),
      })
    },
    onError: (error: unknown) => {
      toast({
        title: t('common.error'),
        description: getApiErrorMessage(error, (key) => t(key), t('drive.importFailed')),
        variant: 'destructive',
      })
    },
  })
}
