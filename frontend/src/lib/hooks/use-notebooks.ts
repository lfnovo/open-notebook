import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { notebooksApi } from '@/lib/api/notebooks'
import { QUERY_KEYS } from '@/lib/api/query-client'
import { useToast } from '@/lib/hooks/use-toast'
import { useTranslation } from '@/lib/hooks/use-translation'
import { getApiErrorKey } from '@/lib/utils/error-handler'
import { CreateNotebookRequest, UpdateNotebookRequest } from '@/lib/types/api'
import { useWorkspaceStore } from '@/lib/stores/workspace-store'

export function useNotebooks(archived?: boolean) {
  const workspaceId = useWorkspaceStore((state) => state.currentWorkspaceId)

  return useQuery({
    queryKey: QUERY_KEYS.workspaceNotebooks(workspaceId, archived),
    queryFn: () =>
      notebooksApi.list({
        archived,
        order_by: 'updated desc',
        workspace_id: workspaceId || undefined,
      }),
  })
}

export function useNotebook(id: string) {
  return useQuery({
    queryKey: QUERY_KEYS.notebook(id),
    queryFn: () => notebooksApi.get(id),
    enabled: !!id,
  })
}

export function useCreateNotebook() {
  const queryClient = useQueryClient()
  const { toast } = useToast()
  const { t } = useTranslation()
  const workspaceId = useWorkspaceStore((state) => state.currentWorkspaceId)

  return useMutation({
    mutationFn: (data: CreateNotebookRequest) =>
      notebooksApi.create({
        ...data,
        workspace_id: data.workspace_id || workspaceId || undefined,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.notebooks })
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.workspaces })
      toast({
        title: t.common.success,
        description: t.notebooks.createSuccess,
      })
    },
    onError: (error: unknown) => {
      toast({
        title: t.common.error,
        description: t(getApiErrorKey(error, t.common.error)),
        variant: 'destructive',
      })
    },
  })
}

export function useUpdateNotebook() {
  const queryClient = useQueryClient()
  const { toast } = useToast()
  const { t } = useTranslation()

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: UpdateNotebookRequest }) =>
      notebooksApi.update(id, data),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.notebooks })
      queryClient.invalidateQueries({ queryKey: ['workspaces'] })
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.notebook(id) })
      toast({
        title: t.common.success,
        description: t.notebooks.updateSuccess,
      })
    },
    onError: (error: unknown) => {
      toast({
        title: t.common.error,
        description: t(getApiErrorKey(error, t.common.error)),
        variant: 'destructive',
      })
    },
  })
}

export function useNotebookDeletePreview(id: string, enabled: boolean = false) {
  return useQuery({
    queryKey: [...QUERY_KEYS.notebook(id), 'delete-preview'],
    queryFn: () => notebooksApi.deletePreview(id),
    enabled: !!id && enabled,
  })
}

export function useDeleteNotebook() {
  const queryClient = useQueryClient()
  const { toast } = useToast()
  const { t } = useTranslation()

  return useMutation({
    mutationFn: ({
      id,
      deleteExclusiveSources = false,
    }: {
      id: string
      deleteExclusiveSources?: boolean
    }) => notebooksApi.delete(id, deleteExclusiveSources),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.notebooks })
      queryClient.invalidateQueries({ queryKey: ['workspaces'] })
      // Also invalidate sources since some may have been deleted
      queryClient.invalidateQueries({ queryKey: ['sources'] })
      toast({
        title: t.common.success,
        description: t.notebooks.deleteSuccess,
      })
    },
    onError: (error: unknown) => {
      toast({
        title: t.common.error,
        description: t(getApiErrorKey(error, t.common.error)),
        variant: 'destructive',
      })
    },
  })
}
