import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { workspacesApi, Workspace } from '@/lib/api/workspaces'

export function useWorkspaces() {
  return useQuery({
    queryKey: ['workspaces'],
    queryFn: async () => {
      const { data } = await workspacesApi.list()
      return data
    },
  })
}

export function useWorkspace(id: string) {
  return useQuery({
    queryKey: ['workspaces', id],
    queryFn: async () => {
      const { data } = await workspacesApi.get(id)
      return data
    },
    enabled: !!id,
  })
}

export function useCreateWorkspace() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (data: { name: string; description?: string; visibility?: string }) => {
      const { data: workspace } = await workspacesApi.create(data)
      return workspace
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workspaces'] })
    },
  })
}

export function useDeleteWorkspace() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => workspacesApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workspaces'] })
    },
  })
}

export function useWorkspaceMembers(workspaceId: string) {
  return useQuery({
    queryKey: ['workspaces', workspaceId, 'members'],
    queryFn: async () => {
      const { data } = await workspacesApi.getMembers(workspaceId)
      return data
    },
    enabled: !!workspaceId,
  })
}
