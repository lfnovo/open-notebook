import { useEffect, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'

import { QUERY_KEYS } from '@/lib/api/query-client'
import { workspacesApi } from '@/lib/api/workspaces'
import { useWorkspaceStore } from '@/lib/stores/workspace-store'

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
