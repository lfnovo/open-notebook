import { useMemo } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { artifactsApi } from '@/lib/api/artifacts'
import { QUERY_KEYS } from '@/lib/api/query-client'
import { useToast } from '@/lib/hooks/use-toast'
import { useTranslation } from '@/lib/hooks/use-translation'
import { getApiErrorKey } from '@/lib/utils/error-handler'
import {
  ACTIVE_ARTIFACT_STATUSES,
  Artifact,
  GenerateArtifactRequest,
} from '@/lib/types/artifacts'

function isActive(artifact: Artifact): boolean {
  const status = artifact.job_status ?? ''
  return (ACTIVE_ARTIFACT_STATUSES as readonly string[]).includes(status)
}

/**
 * List artifacts, polling while any of them is still being generated.
 *
 * Mirrors `usePodcastEpisodes`: polling stops as soon as nothing is active so
 * an idle page makes no requests.
 */
export function useArtifacts(options?: {
  notebookId?: string
  autoRefresh?: boolean
}) {
  const { notebookId, autoRefresh = true } = options ?? {}

  const query = useQuery({
    queryKey: [...QUERY_KEYS.artifacts, { notebookId }],
    queryFn: () => artifactsApi.listArtifacts(notebookId),
    refetchInterval: (current) => {
      if (!autoRefresh) {
        return false
      }

      const data = current.state.data as Artifact[] | undefined
      if (!data || data.length === 0) {
        return false
      }

      return data.some(isActive) ? 5_000 : false
    },
  })

  const artifacts = useMemo(() => query.data ?? [], [query.data])

  return {
    ...query,
    artifacts,
    hasActiveArtifacts: artifacts.some(isActive),
  }
}

export function useGenerateArtifact() {
  const queryClient = useQueryClient()
  const { toast } = useToast()
  const { t } = useTranslation()

  return useMutation({
    mutationFn: (payload: GenerateArtifactRequest) =>
      artifactsApi.generateArtifact(payload),
    onSuccess: async () => {
      await queryClient.refetchQueries({ queryKey: QUERY_KEYS.artifacts })
      toast({
        title: t('artifacts.startedTitle'),
        description: t('artifacts.startedDesc'),
      })
    },
    onError: (error: unknown) => {
      toast({
        title: t('artifacts.startedTitle'),
        description: getApiErrorKey(error, t('common.error')),
        variant: 'destructive',
      })
    },
  })
}

export function useDeleteArtifact() {
  const queryClient = useQueryClient()
  const { toast } = useToast()
  const { t } = useTranslation()

  return useMutation({
    mutationFn: (artifactId: string) => artifactsApi.deleteArtifact(artifactId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.artifacts })
      toast({
        title: t('artifacts.deletedTitle'),
        description: t('artifacts.deletedDesc'),
      })
    },
    onError: (error: unknown) => {
      toast({
        title: t('artifacts.deletedTitle'),
        description: getApiErrorKey(error, t('common.error')),
        variant: 'destructive',
      })
    },
  })
}
