import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { modulesApi } from '@/lib/api/modules'
import { QUERY_KEYS } from '@/lib/api/query-client'
import { useToast } from '@/lib/hooks/use-toast'
import { useTranslation } from '@/lib/hooks/use-translation'
import { getApiErrorKey } from '@/lib/utils/error-handler'
import { CreateModuleRequest, UpdateModuleRequest } from '@/lib/types/api'

export function useModules(archived?: boolean) {
  return useQuery({
    queryKey: [...QUERY_KEYS.modules, { archived }],
    queryFn: () => modulesApi.list({ archived, order_by: 'updated desc' }),
  })
}

export function useModule(id: string) {
  return useQuery({
    queryKey: QUERY_KEYS.module(id),
    queryFn: () => modulesApi.get(id),
    enabled: !!id,
  })
}

export function useCreateModule() {
  const queryClient = useQueryClient()
  const { toast } = useToast()
  const { t } = useTranslation()

  return useMutation({
    mutationFn: (data: CreateModuleRequest) => modulesApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.modules })
      toast({
        title: t.common.success,
        description: t.modules.createSuccess,
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

export function useUpdateModule() {
  const queryClient = useQueryClient()
  const { toast } = useToast()
  const { t } = useTranslation()

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: UpdateModuleRequest }) =>
      modulesApi.update(id, data),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.modules })
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.module(id) })
      toast({
        title: t.common.success,
        description: t.modules.updateSuccess,
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

export function useDeleteModule() {
  const queryClient = useQueryClient()
  const { toast } = useToast()
  const { t } = useTranslation()

  return useMutation({
    mutationFn: (id: string) => modulesApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.modules })
      toast({
        title: t.common.success,
        description: t.modules.deleteSuccess,
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

export function useGenerateOverview() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, modelId }: { id: string; modelId?: string }) =>
      modulesApi.generateOverview(id, modelId),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.modules })
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.module(id) })
    },
  })
}
