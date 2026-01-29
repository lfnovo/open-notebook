import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiKeysApi, SetApiKeyRequest, TestConnectionResult } from '@/lib/api/api-keys'
import { modelsApi } from '@/lib/api/models'
import { useToast } from '@/lib/hooks/use-toast'
import { useTranslation } from '@/lib/hooks/use-translation'
import { getApiErrorKey } from '@/lib/utils/error-handler'
import { MODEL_QUERY_KEYS } from '@/lib/hooks/use-models'

export const API_KEYS_QUERY_KEYS = {
  status: ['api-keys', 'status'] as const,
  envStatus: ['api-keys', 'env-status'] as const,
  modelCount: (provider: string) => ['api-keys', 'model-count', provider] as const,
}

/**
 * Hook to get the status of all API keys (configured/source info)
 */
export function useApiKeysStatus() {
  return useQuery({
    queryKey: API_KEYS_QUERY_KEYS.status,
    queryFn: () => apiKeysApi.getStatus(),
  })
}

/**
 * Hook to get the status of environment variable API keys
 */
export function useEnvStatus() {
  return useQuery({
    queryKey: API_KEYS_QUERY_KEYS.envStatus,
    queryFn: () => apiKeysApi.getEnvStatus(),
  })
}

/**
 * Hook to set/update an API key for a provider
 */
export function useSetApiKey() {
  const queryClient = useQueryClient()
  const { toast } = useToast()
  const { t } = useTranslation()

  return useMutation({
    mutationFn: ({ provider, data }: { provider: string; data: SetApiKeyRequest }) =>
      apiKeysApi.setKey(provider, data),
    onSuccess: () => {
      // Invalidate both API keys status and providers (for models page)
      queryClient.invalidateQueries({ queryKey: API_KEYS_QUERY_KEYS.status })
      queryClient.invalidateQueries({ queryKey: API_KEYS_QUERY_KEYS.envStatus })
      queryClient.invalidateQueries({ queryKey: MODEL_QUERY_KEYS.providers })
      toast({
        title: t.common.success,
        description: t.apiKeys.saveSuccess,
      })
    },
    onError: (error: unknown) => {
      toast({
        title: t.common.error,
        description: getApiErrorKey(error, t.common.error),
        variant: 'destructive',
      })
    },
  })
}

/**
 * Hook to delete an API key for a provider
 */
export function useDeleteApiKey() {
  const queryClient = useQueryClient()
  const { toast } = useToast()
  const { t } = useTranslation()

  return useMutation({
    mutationFn: ({ provider, serviceType }: { provider: string; serviceType?: string }) =>
      apiKeysApi.deleteKey(provider, serviceType),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: API_KEYS_QUERY_KEYS.status })
      queryClient.invalidateQueries({ queryKey: API_KEYS_QUERY_KEYS.envStatus })
      queryClient.invalidateQueries({ queryKey: MODEL_QUERY_KEYS.providers })
      toast({
        title: t.common.success,
        description: t.apiKeys.deleteSuccess,
      })
    },
    onError: (error: unknown) => {
      toast({
        title: t.common.error,
        description: getApiErrorKey(error, t.common.error),
        variant: 'destructive',
      })
    },
  })
}

/**
 * Hook to migrate API keys from environment variables to database
 */
export function useMigrateApiKeys() {
  const queryClient = useQueryClient()
  const { toast } = useToast()
  const { t } = useTranslation()

  return useMutation({
    mutationFn: () => apiKeysApi.migrate(),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: API_KEYS_QUERY_KEYS.status })
      queryClient.invalidateQueries({ queryKey: API_KEYS_QUERY_KEYS.envStatus })
      queryClient.invalidateQueries({ queryKey: MODEL_QUERY_KEYS.providers })

      const migratedCount = result.migrated.length
      const skippedCount = result.skipped.length
      const errorCount = result.errors.length

      if (migratedCount > 0) {
        toast({
          title: t.common.success,
          description: t.apiKeys.migrationSuccess.replace('{count}', migratedCount.toString()),
        })
      }

      if (errorCount > 0) {
        toast({
          title: t.common.warning,
          description: t.apiKeys.migrationErrors.replace('{count}', errorCount.toString()),
          variant: 'destructive',
        })
      }

      if (migratedCount === 0 && skippedCount > 0 && errorCount === 0) {
        toast({
          title: t.common.success,
          description: t.apiKeys.migrationNothingToMigrate,
        })
      }
    },
    onError: (error: unknown) => {
      toast({
        title: t.common.error,
        description: getApiErrorKey(error, t.common.error),
        variant: 'destructive',
      })
    },
  })
}

/**
 * Hook to test connection for a provider
 */
export function useTestConnection() {
  const { toast } = useToast()
  const { t } = useTranslation()
  const [testResults, setTestResults] = useState<Record<string, TestConnectionResult>>({})

  const mutation = useMutation({
    mutationFn: (provider: string) => apiKeysApi.testConnection(provider),
    onSuccess: (result) => {
      setTestResults(prev => ({ ...prev, [result.provider]: result }))
      if (result.success) {
        toast({
          title: t.common.success,
          description: t.apiKeys.testSuccess,
        })
      } else {
        toast({
          title: t.common.error,
          description: result.message || t.apiKeys.testFailed,
          variant: 'destructive',
        })
      }
    },
    onError: (error: unknown) => {
      toast({
        title: t.common.error,
        description: getApiErrorKey(error, t.apiKeys.testFailed),
        variant: 'destructive',
      })
    },
  })

  return {
    testConnection: mutation.mutate,
    testConnectionAsync: mutation.mutateAsync,
    isPending: mutation.isPending,
    testResults,
    clearResult: (provider: string) => {
      setTestResults(prev => {
        const { [provider]: _removed, ...rest } = prev
        return rest
      })
    },
  }
}

/**
 * Hook to get model count for a provider
 */
export function useProviderModelCount(provider: string) {
  return useQuery({
    queryKey: API_KEYS_QUERY_KEYS.modelCount(provider),
    queryFn: () => modelsApi.getProviderModelCount(provider),
    enabled: !!provider,
  })
}

/**
 * Hook to sync models for a provider
 */
export function useSyncModels() {
  const queryClient = useQueryClient()
  const { toast } = useToast()
  const { t } = useTranslation()

  return useMutation({
    mutationFn: (provider: string) => modelsApi.syncProvider(provider),
    onSuccess: (result) => {
      // Invalidate model queries
      queryClient.invalidateQueries({ queryKey: MODEL_QUERY_KEYS.models })
      queryClient.invalidateQueries({ queryKey: API_KEYS_QUERY_KEYS.modelCount(result.provider) })

      if (result.new > 0) {
        toast({
          title: t.common.success,
          description: t.apiKeys.syncSuccess
            .replace('{discovered}', result.discovered.toString())
            .replace('{new}', result.new.toString()),
        })
      } else {
        toast({
          title: t.common.success,
          description: t.apiKeys.syncNoNew.replace('{count}', result.discovered.toString()),
        })
      }
    },
    onError: (error: unknown) => {
      toast({
        title: t.common.error,
        description: getApiErrorKey(error, t.apiKeys.syncFailed),
        variant: 'destructive',
      })
    },
  })
}

/**
 * Hook to sync all providers
 */
export function useSyncAllModels() {
  const queryClient = useQueryClient()
  const { toast } = useToast()
  const { t } = useTranslation()

  return useMutation({
    mutationFn: () => modelsApi.syncAll(),
    onSuccess: (result) => {
      // Invalidate all model queries
      queryClient.invalidateQueries({ queryKey: MODEL_QUERY_KEYS.models })
      queryClient.invalidateQueries({ queryKey: ['api-keys', 'model-count'] })

      toast({
        title: t.common.success,
        description: t.apiKeys.syncAllSuccess
          .replace('{discovered}', result.total_discovered.toString())
          .replace('{new}', result.total_new.toString()),
      })
    },
    onError: (error: unknown) => {
      toast({
        title: t.common.error,
        description: getApiErrorKey(error, t.apiKeys.syncFailed),
        variant: 'destructive',
      })
    },
  })
}
