import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { isAxiosError } from 'axios'
import { foldersApi } from '@/lib/api/folders'
import { notebooksApi } from '@/lib/api/notebooks'
import { QUERY_KEYS } from '@/lib/api/query-client'
import { useToast } from '@/lib/hooks/use-toast'
import { useTranslation } from '@/lib/hooks/use-translation'
import { getApiErrorKey } from '@/lib/utils/error-handler'

export function isDuplicateFolderError(error: unknown): boolean {
  return isAxiosError(error) && error.response?.status === 409
}

export function useFolders() {
  return useQuery({
    queryKey: QUERY_KEYS.folders,
    queryFn: () => foldersApi.list(),
  })
}

function useFolderMutationHelpers() {
  const queryClient = useQueryClient()
  const { toast } = useToast()
  const { t } = useTranslation()

  const refresh = () => {
    queryClient.invalidateQueries({ queryKey: QUERY_KEYS.folders })
    queryClient.invalidateQueries({ queryKey: QUERY_KEYS.notebooks })
  }

  // Duplicate-name (409) errors are shown inline by the folder dialog.
  const onError = (error: unknown) => {
    if (isDuplicateFolderError(error)) return
    toast({
      title: t('common.error'),
      description: t(getApiErrorKey(error, t('common.error'))),
      variant: 'destructive',
    })
  }

  return { refresh, onError, toast, t }
}

export function useCreateFolder() {
  const { refresh, onError, toast, t } = useFolderMutationHelpers()
  return useMutation({
    mutationFn: (name: string) => foldersApi.create(name),
    onSuccess: () => {
      refresh()
      toast({ title: t('common.success'), description: t('folders.createSuccess') })
    },
    onError,
  })
}

export function useRenameFolder() {
  const { refresh, onError, toast, t } = useFolderMutationHelpers()
  return useMutation({
    mutationFn: ({ id, name }: { id: string; name: string }) => foldersApi.rename(id, name),
    onSuccess: () => {
      refresh()
      toast({ title: t('common.success'), description: t('folders.renameSuccess') })
    },
    onError,
  })
}

export function useDeleteFolder() {
  const { refresh, onError, toast, t } = useFolderMutationHelpers()
  return useMutation({
    mutationFn: (id: string) => foldersApi.delete(id),
    onSuccess: () => {
      refresh()
      toast({ title: t('common.success'), description: t('folders.deleteSuccess') })
    },
    onError,
  })
}

/** Move a notebook into a folder, or out of it with `folderId: null`. */
export function useMoveNotebookToFolder() {
  const { refresh, onError, toast, t } = useFolderMutationHelpers()
  return useMutation({
    mutationFn: ({ notebookId, folderId }: { notebookId: string; folderId: string | null }) =>
      notebooksApi.update(notebookId, { folder_id: folderId }),
    onSuccess: () => {
      refresh()
      toast({ title: t('common.success'), description: t('folders.moveSuccess') })
    },
    onError,
  })
}
