import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { notesApi } from '@/lib/api/notes'
import { QUERY_KEYS } from '@/lib/api/query-client'
import { useToast } from '@/lib/hooks/use-toast'
import { CreateNoteRequest, UpdateNoteRequest } from '@/lib/types/api'

export function useNotes(notebookId?: string) {
  return useQuery({
    queryKey: QUERY_KEYS.notes(notebookId),
    queryFn: () => notesApi.list({ notebook_id: notebookId }),
    enabled: !!notebookId,
  })
}

export function useNote(id: string) {
  return useQuery({
    queryKey: QUERY_KEYS.note(id),
    queryFn: () => notesApi.get(id),
    enabled: !!id,
  })
}

export function useCreateNote() {
  const queryClient = useQueryClient()
  const { toast } = useToast()

  return useMutation({
    mutationFn: (data: CreateNoteRequest) => notesApi.create(data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ 
        queryKey: QUERY_KEYS.notes(variables.notebook_id) 
      })
      toast({
        title: 'Success',
        description: 'Note created successfully',
      })
    },
    onError: () => {
      toast({
        title: 'Error',
        description: 'Failed to create note',
        variant: 'destructive',
      })
    },
  })
}

export function useUpdateNote() {
  const queryClient = useQueryClient()
  const { toast } = useToast()

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: UpdateNoteRequest }) =>
      notesApi.update(id, data),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.notes() })
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.note(id) })
      toast({
        title: 'Success',
        description: 'Note updated successfully',
      })
    },
    onError: () => {
      toast({
        title: 'Error',
        description: 'Failed to update note',
        variant: 'destructive',
      })
    },
  })
}

export function useDeleteNote() {
  const queryClient = useQueryClient()
  const { toast } = useToast()

  return useMutation({
    mutationFn: (id: string) => notesApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.notes() })
      toast({
        title: 'Success',
        description: 'Note deleted successfully',
      })
    },
    onError: () => {
      toast({
        title: 'Error',
        description: 'Failed to delete note',
        variant: 'destructive',
      })
    },
  })
}