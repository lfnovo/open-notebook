import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { sourcesApi } from '@/lib/api/sources'
import { QUERY_KEYS } from '@/lib/api/query-client'
import { useToast } from '@/lib/hooks/use-toast'
import { 
  CreateSourceRequest, 
  UpdateSourceRequest, 
  SourceResponse,
  SourceStatusResponse 
} from '@/lib/types/api'

export function useSources(notebookId?: string) {
  return useQuery({
    queryKey: QUERY_KEYS.sources(notebookId),
    queryFn: () => sourcesApi.list({ notebook_id: notebookId }),
    enabled: !!notebookId,
    staleTime: 5 * 1000, // 5 seconds - more responsive for real-time source updates
    refetchOnWindowFocus: true, // Refetch when user comes back to the tab
  })
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

  return useMutation({
    mutationFn: (data: CreateSourceRequest) => sourcesApi.create(data),
    onSuccess: (result: SourceResponse, variables) => {
      // Invalidate queries for all relevant notebooks with immediate refetch
      if (variables.notebooks) {
        variables.notebooks.forEach(notebookId => {
          queryClient.invalidateQueries({
            queryKey: QUERY_KEYS.sources(notebookId),
            refetchType: 'active' // Refetch active queries immediately
          })
        })
      } else if (variables.notebook_id) {
        queryClient.invalidateQueries({
          queryKey: QUERY_KEYS.sources(variables.notebook_id),
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
          title: 'Source Queued',
          description: 'Source submitted for background processing. You can monitor progress in the sources list.',
        })
      } else {
        toast({
          title: 'Success',
          description: 'Source added successfully',
        })
      }
    },
    onError: () => {
      toast({
        title: 'Error',
        description: 'Failed to add source',
        variant: 'destructive',
      })
    },
  })
}

export function useUpdateSource() {
  const queryClient = useQueryClient()
  const { toast } = useToast()

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: UpdateSourceRequest }) =>
      sourcesApi.update(id, data),
    onSuccess: (_, { id }) => {
      // Invalidate ALL sources queries (both general and notebook-specific)
      queryClient.invalidateQueries({ queryKey: ['sources'] })
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.source(id) })
      toast({
        title: 'Success',
        description: 'Source updated successfully',
      })
    },
    onError: () => {
      toast({
        title: 'Error',
        description: 'Failed to update source',
        variant: 'destructive',
      })
    },
  })
}

export function useDeleteSource() {
  const queryClient = useQueryClient()
  const { toast } = useToast()

  return useMutation({
    mutationFn: (id: string) => sourcesApi.delete(id),
    onSuccess: (_, id) => {
      // Invalidate ALL sources queries (both general and notebook-specific)
      queryClient.invalidateQueries({ queryKey: ['sources'] })
      // Also invalidate the specific source
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.source(id) })
      toast({
        title: 'Success',
        description: 'Source deleted successfully',
      })
    },
    onError: () => {
      toast({
        title: 'Error',
        description: 'Failed to delete source',
        variant: 'destructive',
      })
    },
  })
}

export function useFileUpload() {
  const queryClient = useQueryClient()
  const { toast } = useToast()

  return useMutation({
    mutationFn: ({ file, notebookId }: { file: File; notebookId: string }) =>
      sourcesApi.upload(file, notebookId),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ 
        queryKey: QUERY_KEYS.sources(variables.notebookId) 
      })
      toast({
        title: 'Success',
        description: 'File uploaded successfully',
      })
    },
    onError: () => {
      toast({
        title: 'Error',
        description: 'Failed to upload file',
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
        title: 'Source Retry Queued',
        description: 'The source has been requeued for processing.',
      })
    },
    onError: () => {
      toast({
        title: 'Retry Failed',
        description: 'Failed to retry source processing. Please try again.',
        variant: 'destructive',
      })
    },
  })
}

export function useAddSourcesToNotebook() {
  const queryClient = useQueryClient()
  const { toast } = useToast()

  return useMutation({
    mutationFn: async ({ notebookId, sourceIds }: { notebookId: string; sourceIds: string[] }) => {
      const { notebooksApi } = await import('@/lib/api/notebooks')

      // Use Promise.allSettled to handle partial failures gracefully
      const results = await Promise.allSettled(
        sourceIds.map(sourceId => notebooksApi.addSource(notebookId, sourceId))
      )

      // Count successes and failures
      const successes = results.filter(r => r.status === 'fulfilled').length
      const failures = results.filter(r => r.status === 'rejected').length

      return { successes, failures, total: sourceIds.length }
    },
    onSuccess: (result, { notebookId, sourceIds }) => {
      // Invalidate ALL sources queries to refresh all lists
      queryClient.invalidateQueries({ queryKey: ['sources'] })
      // Specifically invalidate the notebook's sources
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.sources(notebookId) })
      // Invalidate each affected source
      sourceIds.forEach(sourceId => {
        queryClient.invalidateQueries({ queryKey: QUERY_KEYS.source(sourceId) })
      })

      // Show appropriate toast based on results
      if (result.failures === 0) {
        toast({
          title: 'Success',
          description: `${result.successes} source${result.successes > 1 ? 's' : ''} added to notebook`,
        })
      } else if (result.successes === 0) {
        toast({
          title: 'Error',
          description: 'Failed to add sources to notebook',
          variant: 'destructive',
        })
      } else {
        toast({
          title: 'Partial Success',
          description: `${result.successes} source${result.successes > 1 ? 's' : ''} added, ${result.failures} failed`,
          variant: 'default',
        })
      }
    },
    onError: () => {
      toast({
        title: 'Error',
        description: 'Failed to add sources to notebook',
        variant: 'destructive',
      })
    },
  })
}

export function useRemoveSourceFromNotebook() {
  const queryClient = useQueryClient()
  const { toast } = useToast()

  return useMutation({
    mutationFn: async ({ notebookId, sourceId }: { notebookId: string; sourceId: string }) => {
      // This will call the API we created
      const { notebooksApi } = await import('@/lib/api/notebooks')
      return notebooksApi.removeSource(notebookId, sourceId)
    },
    onSuccess: (_, { notebookId, sourceId }) => {
      // Invalidate ALL sources queries to refresh all lists
      queryClient.invalidateQueries({ queryKey: ['sources'] })
      // Specifically invalidate the notebook's sources
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.sources(notebookId) })
      // Also invalidate the specific source
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.source(sourceId) })

      toast({
        title: 'Success',
        description: 'Source removed from notebook successfully',
      })
    },
    onError: () => {
      toast({
        title: 'Error',
        description: 'Failed to remove source from notebook',
        variant: 'destructive',
      })
    },
  })
}
