import { useQuery, useMutation, useQueryClient, useInfiniteQuery } from '@tanstack/react-query'
import { useCallback, useMemo } from 'react'
import { sourcesApi } from '@/lib/api/sources'
import { QUERY_KEYS } from '@/lib/api/query-client'
import { useToast } from '@/lib/hooks/use-toast'
import { useTranslation } from '@/lib/hooks/use-translation'
import { getApiErrorKey } from '@/lib/utils/error-handler'
import {
  CreateSourceRequest,
  UpdateSourceRequest,
  SourceResponse,
  SourceStatusResponse,
  SourceListResponse
} from '@/lib/types/api'

const MODULE_SOURCES_PAGE_SIZE = 30

export function useSources(moduleId?: string) {
  return useQuery({
    queryKey: QUERY_KEYS.sources(moduleId),
    queryFn: () => sourcesApi.list({ module_id: moduleId }),
    enabled: !!moduleId,
    staleTime: 5 * 1000, // 5 seconds - more responsive for real-time source updates
    refetchOnWindowFocus: true, // Refetch when user comes back to the tab
  })
}

/**
 * Hook for fetching module sources with infinite scroll pagination.
 * Returns flattened sources array and pagination controls.
 */
export function useModuleSources(moduleId: string) {
  const queryClient = useQueryClient()

  const query = useInfiniteQuery({
    queryKey: QUERY_KEYS.sourcesInfinite(moduleId),
    queryFn: async ({ pageParam = 0 }) => {
      const data = await sourcesApi.list({
        module_id: moduleId,
        limit: MODULE_SOURCES_PAGE_SIZE,
        offset: pageParam,
        sort_by: 'updated',
        sort_order: 'desc',
      })
      return {
        sources: data,
        nextOffset: data.length === MODULE_SOURCES_PAGE_SIZE ? pageParam + data.length : undefined,
      }
    },
    initialPageParam: 0,
    getNextPageParam: (lastPage) => lastPage.nextOffset,
    enabled: !!moduleId,
    staleTime: 5 * 1000,
    refetchOnWindowFocus: true,
  })

  // Flatten all pages into a single array (memoized to prevent infinite re-renders)
  const sources: SourceListResponse[] = useMemo(
    () => query.data?.pages.flatMap(page => page.sources) ?? [],
    [query.data?.pages]
  )

  // Refetch function that resets to first page
  const refetch = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: QUERY_KEYS.sourcesInfinite(moduleId) })
  }, [queryClient, moduleId])

  return {
    sources,
    isLoading: query.isLoading,
    isFetchingNextPage: query.isFetchingNextPage,
    hasNextPage: query.hasNextPage,
    fetchNextPage: query.fetchNextPage,
    refetch,
    error: query.error,
  }
}

export function useSource(id: string) {
  return useQuery({
    queryKey: QUERY_KEYS.source(id),
    queryFn: () => sourcesApi.get(id),
    enabled: !!id,
    staleTime: 30 * 1000, // 30 seconds - shorter stale time for more responsive updates
    refetchOnWindowFocus: true, // Refetch when user comes back to the tab
  })
}

export function useCreateSource() {
  const queryClient = useQueryClient()
  const { toast } = useToast()
  const { t } = useTranslation()

  return useMutation({
    mutationFn: (data: CreateSourceRequest) => sourcesApi.create(data),
    onSuccess: (result: SourceResponse, variables) => {
      // Invalidate queries for all relevant modules with immediate refetch
      if (variables.modules) {
        variables.modules.forEach(moduleId => {
          queryClient.invalidateQueries({
            queryKey: QUERY_KEYS.sources(moduleId),
            refetchType: 'active' // Refetch active queries immediately
          })
        })
      } else if (variables.module_id) {
        queryClient.invalidateQueries({
          queryKey: QUERY_KEYS.sources(variables.module_id),
          refetchType: 'active'
        })
      }

      // Invalidate general sources query too with immediate refetch
      queryClient.invalidateQueries({
        queryKey: QUERY_KEYS.sources(),
        refetchType: 'active'
      })

      // Show different messages based on processing mode
      if (variables.async_processing) {
        toast({
          title: t.sources.sourceQueued,
          description: t.sources.sourceQueuedDesc,
        })
      } else {
        toast({
          title: t.common.success,
          description: t.sources.sourceAddedSuccess,
        })
      }
    },
    onError: (error: unknown) => {
      toast({
        title: t.common.error,
        description: t(getApiErrorKey(error, t.sources.failedToAddSource)),
        variant: 'destructive',
      })
    },
  })
}

export function useUpdateSource() {
  const queryClient = useQueryClient()
  const { toast } = useToast()
  const { t } = useTranslation()

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: UpdateSourceRequest }) =>
      sourcesApi.update(id, data),
    onSuccess: (_, { id }) => {
      // Invalidate ALL sources queries (both general and module-specific)
      queryClient.invalidateQueries({ queryKey: ['sources'] })
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.source(id) })
      toast({
        title: t.common.success,
        description: t.sources.sourceUpdatedSuccess,
      })
    },
    onError: (error: unknown) => {
      toast({
        title: t.common.error,
        description: t(getApiErrorKey(error, t.sources.failedToUpdateSource)),
        variant: 'destructive',
      })
    },
  })
}

export function useDeleteSource() {
  const queryClient = useQueryClient()
  const { toast } = useToast()
  const { t } = useTranslation()

  return useMutation({
    mutationFn: (id: string) => sourcesApi.delete(id),
    onSuccess: (_, id) => {
      // Invalidate ALL sources queries (both general and module-specific)
      queryClient.invalidateQueries({ queryKey: ['sources'] })
      // Also invalidate the specific source
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.source(id) })
      toast({
        title: t.common.success,
        description: t.sources.sourceDeletedSuccess,
      })
    },
    onError: (error: unknown) => {
      toast({
        title: t.common.error,
        description: t(getApiErrorKey(error, t.sources.failedToDeleteSource)),
        variant: 'destructive',
      })
    },
  })
}

export function useFileUpload() {
  const queryClient = useQueryClient()
  const { toast } = useToast()
  const { t } = useTranslation()

  return useMutation({
    mutationFn: ({ file, moduleId }: { file: File; moduleId: string }) =>
      sourcesApi.upload(file, moduleId),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ 
        queryKey: QUERY_KEYS.sources(variables.moduleId) 
      })
      toast({
        title: t.common.success,
        description: t.sources.fileUploadedSuccess,
      })
    },
    onError: (error: unknown) => {
      toast({
        title: t.common.error,
        description: t(getApiErrorKey(error, t.sources.failedToUploadFile)),
        variant: 'destructive',
      })
    },
  })
}

export function useSourceStatus(sourceId: string, enabled = true) {
  return useQuery({
    queryKey: ['sources', sourceId, 'status'],
    queryFn: () => sourcesApi.status(sourceId),
    enabled: !!sourceId && enabled,
    refetchInterval: (query) => {
      // Auto-refresh every 2 seconds if processing
      // The query.state.data contains the SourceStatusResponse
      const data = query.state.data as SourceStatusResponse | undefined
      if (data?.status === 'running' || data?.status === 'queued' || data?.status === 'new') {
        return 2000
      }
      // No auto-refresh if completed, failed, or unknown
      return false
    },
    staleTime: 0, // Always consider status data stale for real-time updates
    retry: (failureCount, error) => {
      // Don't retry on 404 (source not found)
      const axiosError = error as { response?: { status?: number } }
      if (axiosError?.response?.status === 404) {
        return false
      }
      return failureCount < 3
    },
  })
}

export function useRetrySource() {
  const queryClient = useQueryClient()
  const { toast } = useToast()
  const { t } = useTranslation()

  return useMutation({
    mutationFn: (sourceId: string) => sourcesApi.retry(sourceId),
    onSuccess: (result, sourceId) => {
      // Invalidate status query to refetch latest status
      queryClient.invalidateQueries({
        queryKey: ['sources', sourceId, 'status']
      })
      // Invalidate ALL sources queries to refresh the UI
      queryClient.invalidateQueries({ queryKey: ['sources'] })
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.source(sourceId) })

      toast({
        title: t.sources.sourceRequeued,
        description: t.sources.sourceRequeuedDesc,
      })
    },
    onError: (error: unknown) => {
      toast({
        title: t.common.error,
        description: t(getApiErrorKey(error, t.sources.failedToRetry)),
        variant: 'destructive',
      })
    },
  })
}

export function useAddSourcesToModule() {
  const queryClient = useQueryClient()
  const { toast } = useToast()
  const { t } = useTranslation()

  return useMutation({
    mutationFn: async ({ moduleId, sourceIds }: { moduleId: string; sourceIds: string[] }) => {
      const { modulesApi } = await import('@/lib/api/modules')

      // Use Promise.allSettled to handle partial failures gracefully
      const results = await Promise.allSettled(
        sourceIds.map(sourceId => modulesApi.addSource(moduleId, sourceId))
      )

      // Count successes and failures
      const successes = results.filter(r => r.status === 'fulfilled').length
      const failures = results.filter(r => r.status === 'rejected').length

      return { successes, failures, total: sourceIds.length }
    },
    onSuccess: (result, { moduleId, sourceIds }) => {
      // Invalidate ALL sources queries to refresh all lists
      queryClient.invalidateQueries({ queryKey: ['sources'] })
      // Specifically invalidate the module's sources
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.sources(moduleId) })
      // Invalidate each affected source
      sourceIds.forEach(sourceId => {
        queryClient.invalidateQueries({ queryKey: QUERY_KEYS.source(sourceId) })
      })

      // Show appropriate toast based on results
      if (result.failures === 0) {
        toast({
          title: t.common.success,
          description: t.sources.sourcesAddedToModule.replace('{count}', result.successes.toString()),
        })
      } else if (result.successes === 0) {
        toast({
          title: t.common.error,
          description: t.sources.failedToAddSourcesToModule,
          variant: 'destructive',
        })
      } else {
        toast({
          title: t.common.success,
          description: t.sources.partialAddSuccess
            .replace('{success}', result.successes.toString())
            .replace('{failed}', result.failures.toString()),
          variant: 'default',
        })
      }
    },
    onError: (error: unknown) => {
      toast({
        title: t.common.error,
        description: t(getApiErrorKey(error, t.sources.failedToAddSourcesToModule)),
        variant: 'destructive',
      })
    },
  })
}

export function useRemoveSourceFromModule() {
  const queryClient = useQueryClient()
  const { toast } = useToast()
  const { t } = useTranslation()

  return useMutation({
    mutationFn: async ({ moduleId, sourceId }: { moduleId: string; sourceId: string }) => {
      // This will call the API we created
      const { modulesApi } = await import('@/lib/api/modules')
      return modulesApi.removeSource(moduleId, sourceId)
    },
    onSuccess: (_, { moduleId, sourceId }) => {
      // Invalidate ALL sources queries to refresh all lists
      queryClient.invalidateQueries({ queryKey: ['sources'] })
      // Specifically invalidate the module's sources
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.sources(moduleId) })
      // Also invalidate the specific source
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.source(sourceId) })

      toast({
        title: t.common.success,
        description: t.sources.sourceRemovedFromModule,
      })
    },
    onError: (error: unknown) => {
      toast({
        title: t.common.error,
        description: t(getApiErrorKey(error, t.sources.failedToRemoveSourceFromModule)),
        variant: 'destructive',
      })
    },
  })
}