import { useEffect, useMemo } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { QUERY_KEYS } from '@/lib/api/query-client'
import { WorkspaceResourceMoveRequest, workspacesApi } from '@/lib/api/workspaces'
import { useWorkspaceStore } from '@/lib/stores/workspace-store'
import { useToast } from './use-toast'
import { useTranslation } from './use-translation'
import { getApiErrorKey } from '../utils/error-handler'

export function useWorkspaces() {
  return useQuery({
    queryKey: QUERY_KEYS.workspaces,
    queryFn: () => workspacesApi.list(),
  })
}

export function useCurrentWorkspace() {
  const currentWorkspaceId = useWorkspaceStore((state) => state.currentWorkspaceId)
  const setCurrentWorkspaceId = useWorkspaceStore((state) => state.setCurrentWorkspaceId)
  const query = useWorkspaces()

  const currentWorkspace = useMemo(
    () => query.data?.items.find((workspace) => workspace.id === currentWorkspaceId) ?? null,
    [currentWorkspaceId, query.data?.items]
  )

  useEffect(() => {
    if (currentWorkspaceId || !query.data?.items.length) {
      return
    }
    setCurrentWorkspaceId(query.data.items[0].id)
  }, [currentWorkspaceId, query.data?.items, setCurrentWorkspaceId])

  return {
    ...query,
    currentWorkspace,
    currentWorkspaceId,
    setCurrentWorkspaceId,
  }
}

export function useMoveWorkspaceResource() {
  const queryClient = useQueryClient()
  const setCurrentWorkspaceId = useWorkspaceStore((state) => state.setCurrentWorkspaceId)
  const { toast } = useToast()
  const { t } = useTranslation()

  return useMutation({
    mutationFn: ({
      workspaceId,
      data,
    }: {
      workspaceId: string
      data: WorkspaceResourceMoveRequest
    }) => workspacesApi.moveResource(workspaceId, data),
    onSuccess: (response) => {
      setCurrentWorkspaceId(response.target_workspace_id)
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.workspaces })
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.notebooks })
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.notebook(response.resource_id) })
      toast({
        title: t.common.success,
        description: t.notebooks.moveNotebookSuccess,
      })
    },
    onError: (error: unknown) => {
      toast({
        title: t.common.error,
        description: t(getApiErrorKey(error, t.notebooks.failedToMoveNotebook)),
        variant: 'destructive',
      })
    },
  })
}
