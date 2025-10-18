import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { notebooksApi } from '@/lib/api/notebooks'
import { QUERY_KEYS } from '@/lib/api/query-client'
import { useToast } from '@/lib/hooks/use-toast'
import { CreateNotebookRequest, UpdateNotebookRequest } from '@/lib/types/api'

export function useNotebooks(archived?: boolean) {
  return useQuery({
    queryKey: [...QUERY_KEYS.notebooks, { archived }],
    queryFn: () => notebooksApi.list({ archived, order_by: 'updated desc' }),
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

  return useMutation({
    mutationFn: (data: CreateNotebookRequest) => notebooksApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.notebooks })
      toast({
        title: 'Success',
        description: 'Notebook created successfully',
      })
    },
    onError: () => {
      toast({
        title: 'Error',
        description: 'Failed to create notebook',
        variant: 'destructive',
      })
    },
  })
}

export function useUpdateNotebook() {
  const queryClient = useQueryClient()
  const { toast } = useToast()

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: UpdateNotebookRequest }) =>
      notebooksApi.update(id, data),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.notebooks })
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.notebook(id) })
      toast({
        title: 'Success',
        description: 'Notebook updated successfully',
      })
    },
    onError: () => {
      toast({
        title: 'Error',
        description: 'Failed to update notebook',
        variant: 'destructive',
      })
    },
  })
}

export function useDeleteNotebook() {
  const queryClient = useQueryClient()
  const { toast } = useToast()

  return useMutation({
    mutationFn: (id: string) => notebooksApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.notebooks })
      toast({
        title: 'Success',
        description: 'Notebook deleted successfully',
      })
    },
    onError: () => {
      toast({
        title: 'Error',
        description: 'Failed to delete notebook',
        variant: 'destructive',
      })
    },
  })
}