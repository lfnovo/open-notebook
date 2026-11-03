import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { isAxiosError } from 'axios'
import { sectionsApi } from '@/lib/api/sections'
import { QUERY_KEYS } from '@/lib/api/query-client'
import { useToast } from '@/lib/hooks/use-toast'
import { useTranslation } from '@/lib/hooks/use-translation'
import { getApiErrorKey } from '@/lib/utils/error-handler'

export function isDuplicateSectionError(error: unknown): boolean {
  return isAxiosError(error) && error.response?.status === 409
}

export function useSections() {
  return useQuery({
    queryKey: QUERY_KEYS.sections,
    queryFn: () => sectionsApi.list(),
  })
}

function useSectionMutationHelpers() {
  const queryClient = useQueryClient()
  const { toast } = useToast()
  const { t } = useTranslation()

  // Deleting a section changes its folders' grouping too.
  const refresh = () => {
    queryClient.invalidateQueries({ queryKey: QUERY_KEYS.sections })
    queryClient.invalidateQueries({ queryKey: QUERY_KEYS.folders })
  }

  // Duplicate-name (409) errors are shown inline by the section dialog.
  const onError = (error: unknown) => {
    if (isDuplicateSectionError(error)) return
    toast({
      title: t('common.error'),
      description: t(getApiErrorKey(error, t('common.error'))),
      variant: 'destructive',
    })
  }

  return { refresh, onError, toast, t }
}

export function useCreateSection() {
  const { refresh, onError, toast, t } = useSectionMutationHelpers()
  return useMutation({
    mutationFn: (name: string) => sectionsApi.create(name),
    onSuccess: () => {
      refresh()
      toast({ title: t('common.success'), description: t('sections.createSuccess') })
    },
    onError,
  })
}

export function useRenameSection() {
  const { refresh, onError, toast, t } = useSectionMutationHelpers()
  return useMutation({
    mutationFn: ({ id, name }: { id: string; name: string }) => sectionsApi.rename(id, name),
    onSuccess: () => {
      refresh()
      toast({ title: t('common.success'), description: t('sections.renameSuccess') })
    },
    onError,
  })
}

export function useDeleteSection() {
  const { refresh, onError, toast, t } = useSectionMutationHelpers()
  return useMutation({
    mutationFn: (id: string) => sectionsApi.delete(id),
    onSuccess: () => {
      refresh()
      toast({ title: t('common.success'), description: t('sections.deleteSuccess') })
    },
    onError,
  })
}
