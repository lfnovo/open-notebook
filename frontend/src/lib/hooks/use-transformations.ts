import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { transformationsApi } from '@/lib/api/transformations'
import { useToast } from '@/lib/hooks/use-toast'
import { useTranslation } from '@/lib/hooks/use-translation'
import { getApiErrorKey } from '@/lib/utils/error-handler'
import {
  CreateTransformationRequest,
  UpdateTransformationRequest,
  ExecuteTransformationRequest
} from '@/lib/types/transformations'

// Add to QUERY_KEYS in query-client.ts
export const TRANSFORMATION_QUERY_KEYS = {
  transformations: ['transformations'] as const,
  transformation: (id: string) => ['transformations', id] as const,
  defaultPrompt: ['transformations', 'default-prompt'] as const,
}

export function useTransformations() {
  return useQuery({
    queryKey: TRANSFORMATION_QUERY_KEYS.transformations,
    queryFn: () => transformationsApi.list(),
  })
}

export function useTransformation(id?: string, options?: { enabled?: boolean }) {
  const transformationId = id ?? ''
  return useQuery({
    queryKey: TRANSFORMATION_QUERY_KEYS.transformation(transformationId),
    queryFn: () => transformationsApi.get(transformationId),
    enabled: !!transformationId && (options?.enabled ?? true),
  })
}

export function useCreateTransformation() {
  const queryClient = useQueryClient()
  const { toast } = useToast()
  const { t } = useTranslation()

  return useMutation({
    mutationFn: (data: CreateTransformationRequest) => transformationsApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: TRANSFORMATION_QUERY_KEYS.transformations })
      toast({
        title: t.common.success,
        description: t.transformations.createSuccess,
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

export function useUpdateTransformation() {
  const queryClient = useQueryClient()
  const { toast } = useToast()
  const { t } = useTranslation()

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: UpdateTransformationRequest }) =>
      transformationsApi.update(id, data),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: TRANSFORMATION_QUERY_KEYS.transformations })
      queryClient.invalidateQueries({ queryKey: TRANSFORMATION_QUERY_KEYS.transformation(id) })
      toast({
        title: t.common.success,
        description: t.transformations.updateSuccess,
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

export function useDeleteTransformation() {
  const queryClient = useQueryClient()
  const { toast } = useToast()
  const { t } = useTranslation()

  return useMutation({
    mutationFn: (id: string) => transformationsApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: TRANSFORMATION_QUERY_KEYS.transformations })
      toast({
        title: t.common.success,
        description: t.transformations.deleteSuccess,
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

export function useExecuteTransformation() {
  const { toast } = useToast()
  const { t } = useTranslation()

  return useMutation({
    mutationFn: (data: ExecuteTransformationRequest) => transformationsApi.execute(data),
    onError: (error: unknown) => {
      toast({
        title: t.common.error,
        description: t(getApiErrorKey(error, t.common.error)),
        variant: 'destructive',
      })
    },
  })
}

export function useDefaultPrompt() {
  return useQuery({
    queryKey: TRANSFORMATION_QUERY_KEYS.defaultPrompt,
    queryFn: () => transformationsApi.getDefaultPrompt(),
  })
}

export function useUpdateDefaultPrompt() {
  const queryClient = useQueryClient()
  const { toast } = useToast()
  const { t } = useTranslation()

  return useMutation({
    mutationFn: (prompt: { transformation_instructions: string }) => transformationsApi.updateDefaultPrompt(prompt),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: TRANSFORMATION_QUERY_KEYS.defaultPrompt })
      toast({
        title: t.common.success,
        description: t.transformations.updateSuccess,
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
