import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { modelsApi } from '@/lib/api/models'
import { useToast } from '@/lib/hooks/use-toast'
import { CreateModelRequest, ModelDefaults } from '@/lib/types/models'

export const MODEL_QUERY_KEYS = {
  models: ['models'] as const,
  model: (id: string) => ['models', id] as const,
  defaults: ['models', 'defaults'] as const,
  providers: ['models', 'providers'] as const,
}

export function useModels() {
  return useQuery({
    queryKey: MODEL_QUERY_KEYS.models,
    queryFn: () => modelsApi.list(),
  })
}

export function useModel(id: string) {
  return useQuery({
    queryKey: MODEL_QUERY_KEYS.model(id),
    queryFn: () => modelsApi.get(id),
    enabled: !!id,
  })
}

export function useCreateModel() {
  const queryClient = useQueryClient()
  const { toast } = useToast()

  return useMutation({
    mutationFn: (data: CreateModelRequest) => modelsApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: MODEL_QUERY_KEYS.models })
      toast({
        title: 'Success',
        description: 'Model created successfully',
      })
    },
    onError: (error: unknown) => {
      const errorMessage = (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Failed to create model'
      toast({
        title: 'Error',
        description: errorMessage,
        variant: 'destructive',
      })
    },
  })
}

export function useDeleteModel() {
  const queryClient = useQueryClient()
  const { toast } = useToast()

  return useMutation({
    mutationFn: (id: string) => modelsApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: MODEL_QUERY_KEYS.models })
      queryClient.invalidateQueries({ queryKey: MODEL_QUERY_KEYS.defaults })
      toast({
        title: 'Success',
        description: 'Model deleted successfully',
      })
    },
    onError: () => {
      toast({
        title: 'Error',
        description: 'Failed to delete model',
        variant: 'destructive',
      })
    },
  })
}

export function useModelDefaults() {
  return useQuery({
    queryKey: MODEL_QUERY_KEYS.defaults,
    queryFn: () => modelsApi.getDefaults(),
  })
}

export function useUpdateModelDefaults() {
  const queryClient = useQueryClient()
  const { toast } = useToast()

  return useMutation({
    mutationFn: (data: Partial<ModelDefaults>) => modelsApi.updateDefaults(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: MODEL_QUERY_KEYS.defaults })
      toast({
        title: 'Success',
        description: 'Default models updated successfully',
      })
    },
    onError: () => {
      toast({
        title: 'Error',
        description: 'Failed to update default models',
        variant: 'destructive',
      })
    },
  })
}

export function useProviders() {
  return useQuery({
    queryKey: MODEL_QUERY_KEYS.providers,
    queryFn: () => modelsApi.getProviders(),
  })
}
