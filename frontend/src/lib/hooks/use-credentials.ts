import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  credentialsApi,
  CreateCredentialRequest,
  UpdateCredentialRequest,
  TestConnectionResult,
  RegisterModelData,
} from '@/lib/api/credentials'
import { useToast } from '@/lib/hooks/use-toast'
import { useTranslation } from '@/lib/hooks/use-translation'
import { getApiErrorKey } from '@/lib/utils/error-handler'
import { MODEL_QUERY_KEYS } from '@/lib/hooks/use-models'

export const CREDENTIAL_QUERY_KEYS = {
  all: ['credentials'] as const,
  status: ['credentials', 'status'] as const,
  envStatus: ['credentials', 'env-status'] as const,
  byProvider: (provider: string) => ['credentials', 'provider', provider] as const,
  detail: (id: string) => ['credentials', id] as const,
}

/**
 * Hook to get the configuration status of all providers
 */
export function useCredentialStatus() {
  return useQuery({
    queryKey: CREDENTIAL_QUERY_KEYS.status,
    queryFn: () => credentialsApi.getStatus(),
  })
}

/**
 * Hook to get the environment variable status
 */
export function useEnvStatus() {
  return useQuery({
    queryKey: CREDENTIAL_QUERY_KEYS.envStatus,
    queryFn: () => credentialsApi.getEnvStatus(),
  })
}

/**
 * Hook to list all credentials
 */
export function useCredentials(provider?: string) {
  return useQuery({
    queryKey: provider ? CREDENTIAL_QUERY_KEYS.byProvider(provider) : CREDENTIAL_QUERY_KEYS.all,
    queryFn: () => credentialsApi.list(provider),
  })
}

/**
 * Hook to list credentials for a specific provider.
 * Uses the same list endpoint with provider filter for cache consistency.
 */
export function useCredentialsByProvider(provider: string) {
  return useQuery({
    queryKey: CREDENTIAL_QUERY_KEYS.byProvider(provider),
    queryFn: () => credentialsApi.list(provider),
    enabled: !!provider,
  })
}

/**
 * Hook to get a specific credential
 */
export function useCredential(credentialId: string) {
  return useQuery({
    queryKey: CREDENTIAL_QUERY_KEYS.detail(credentialId),
    queryFn: () => credentialsApi.get(credentialId),
    enabled: !!credentialId,
  })
}

/**
 * Hook to create a new credential
 */
export function useCreateCredential() {
  const queryClient = useQueryClient()
  const { toast } = useToast()
  const { t } = useTranslation()

  return useMutation({
    mutationFn: (data: CreateCredentialRequest) => credentialsApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: CREDENTIAL_QUERY_KEYS.all })
      queryClient.invalidateQueries({ queryKey: MODEL_QUERY_KEYS.providers })
      toast({
        title: t.common.success,
        description: t.apiKeys.configSaveSuccess,
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
 * Hook to update a credential
 */
export function useUpdateCredential() {
  const queryClient = useQueryClient()
  const { toast } = useToast()
  const { t } = useTranslation()

  return useMutation({
    mutationFn: ({
      credentialId,
      data,
    }: {
      credentialId: string
      data: UpdateCredentialRequest
    }) => credentialsApi.update(credentialId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: CREDENTIAL_QUERY_KEYS.all })
      queryClient.invalidateQueries({ queryKey: MODEL_QUERY_KEYS.providers })
      toast({
        title: t.common.success,
        description: t.apiKeys.configUpdateSuccess,
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
 * Hook to delete a credential
 */
export function useDeleteCredential() {
  const queryClient = useQueryClient()
  const { toast } = useToast()
  const { t } = useTranslation()

  return useMutation({
    mutationFn: ({
      credentialId,
      options,
    }: {
      credentialId: string
      options?: { delete_models?: boolean; migrate_to?: string }
    }) => credentialsApi.delete(credentialId, options),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: CREDENTIAL_QUERY_KEYS.all })
      queryClient.invalidateQueries({ queryKey: MODEL_QUERY_KEYS.models })
      queryClient.invalidateQueries({ queryKey: MODEL_QUERY_KEYS.providers })
      toast({
        title: t.common.success,
        description: t.apiKeys.configDeleteSuccess,
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
 * Hook to test a credential's connection
 */
export function useTestCredential() {
  const { toast } = useToast()
  const { t } = useTranslation()
  const [testResults, setTestResults] = useState<Record<string, TestConnectionResult>>({})

  const mutation = useMutation({
    mutationFn: (credentialId: string) => credentialsApi.test(credentialId),
    onSuccess: (result, credentialId) => {
      setTestResults(prev => ({ ...prev, [credentialId]: result }))
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
    testCredential: mutation.mutate,
    testCredentialAsync: mutation.mutateAsync,
    isPending: mutation.isPending,
    testResults,
    clearResult: (credentialId: string) => {
      setTestResults(prev => {
        const { [credentialId]: _removed, ...rest } = prev
        return rest
      })
    },
  }
}

/**
 * Hook to discover models for a credential
 */
export function useDiscoverModels() {
  const { toast } = useToast()
  const { t } = useTranslation()

  return useMutation({
    mutationFn: (credentialId: string) => credentialsApi.discover(credentialId),
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
 * Hook to register discovered models
 */
export function useRegisterModels() {
  const queryClient = useQueryClient()
  const { toast } = useToast()
  const { t } = useTranslation()

  return useMutation({
    mutationFn: ({
      credentialId,
      models,
    }: {
      credentialId: string
      models: RegisterModelData[]
    }) => credentialsApi.registerModels(credentialId, { models }),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: MODEL_QUERY_KEYS.models })
      queryClient.invalidateQueries({ queryKey: CREDENTIAL_QUERY_KEYS.all })

      if (result.created > 0) {
        toast({
          title: t.common.success,
          description: t.apiKeys.syncSuccess
            .replace('{discovered}', (result.created + result.existing).toString())
            .replace('{new}', result.created.toString()),
        })
      } else {
        toast({
          title: t.common.success,
          description: t.apiKeys.syncNoNew.replace('{count}', result.existing.toString()),
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
 * Hook to migrate from environment variables
 */
export function useMigrateFromEnv() {
  const queryClient = useQueryClient()
  const { toast } = useToast()
  const { t } = useTranslation()

  return useMutation({
    mutationFn: () => credentialsApi.migrateFromEnv(),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: CREDENTIAL_QUERY_KEYS.all })
      queryClient.invalidateQueries({ queryKey: CREDENTIAL_QUERY_KEYS.status })
      queryClient.invalidateQueries({ queryKey: CREDENTIAL_QUERY_KEYS.envStatus })
      queryClient.invalidateQueries({ queryKey: MODEL_QUERY_KEYS.models })
      queryClient.invalidateQueries({ queryKey: MODEL_QUERY_KEYS.providers })

      const migratedCount = result.migrated.length
      const errorCount = result.errors?.length ?? 0

      if (errorCount > 0 && migratedCount === 0) {
        toast({
          title: t.common.error,
          description: t.apiKeys.migrationErrors.replace('{count}', errorCount.toString()),
          variant: 'destructive',
        })
      } else if (migratedCount > 0 && errorCount > 0) {
        toast({
          title: t.common.success,
          description: `${t.apiKeys.migrationSuccess.replace('{count}', migratedCount.toString())}. ${t.apiKeys.migrationErrors.replace('{count}', errorCount.toString())}`,
        })
      } else if (migratedCount > 0) {
        toast({
          title: t.common.success,
          description: t.apiKeys.migrationSuccess.replace('{count}', migratedCount.toString()),
        })
      } else {
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
 * Hook to migrate from ProviderConfig
 */
export function useMigrateFromProviderConfig() {
  const queryClient = useQueryClient()
  const { toast } = useToast()
  const { t } = useTranslation()

  return useMutation({
    mutationFn: () => credentialsApi.migrateFromProviderConfig(),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: CREDENTIAL_QUERY_KEYS.all })
      queryClient.invalidateQueries({ queryKey: CREDENTIAL_QUERY_KEYS.status })
      queryClient.invalidateQueries({ queryKey: CREDENTIAL_QUERY_KEYS.envStatus })
      queryClient.invalidateQueries({ queryKey: MODEL_QUERY_KEYS.models })
      queryClient.invalidateQueries({ queryKey: MODEL_QUERY_KEYS.providers })

      const migratedCount = result.migrated.length
      const errorCount = result.errors?.length ?? 0

      if (errorCount > 0 && migratedCount === 0) {
        toast({
          title: t.common.error,
          description: t.apiKeys.migrationErrors.replace('{count}', errorCount.toString()),
          variant: 'destructive',
        })
      } else if (migratedCount > 0 && errorCount > 0) {
        toast({
          title: t.common.success,
          description: `${t.apiKeys.migrationSuccess.replace('{count}', migratedCount.toString())}. ${t.apiKeys.migrationErrors.replace('{count}', errorCount.toString())}`,
        })
      } else if (migratedCount > 0) {
        toast({
          title: t.common.success,
          description: t.apiKeys.migrationSuccess.replace('{count}', migratedCount.toString()),
        })
      } else {
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
