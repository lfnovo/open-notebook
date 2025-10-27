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

export function useNote(id?: string, options?: { enabled?: boolean }) {
  const noteId = id ?? ''
  return useQuery({
    queryKey: QUERY_KEYS.note(noteId),
    queryFn: () => notesApi.get(noteId),
    enabled: !!noteId && (options?.enabled ?? true),
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
      // Invalidate all notes queries (with and without notebook IDs)
      queryClient.invalidateQueries({ queryKey: ['notes'] })
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
