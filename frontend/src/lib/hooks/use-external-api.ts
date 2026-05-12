import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { QUERY_KEYS } from '@/lib/api/query-client'
import {
  externalApi,
  ExternalApiConnectionCreate,
  ExternalApiOutputGenerateRequest,
  ExternalApiSearchRequest,
  ExternalApiSourceCreate,
  ExternalApiTeamGrantCreate,
} from '@/lib/api/external-api'
import { useToast } from '@/lib/hooks/use-toast'
import { useTranslation } from '@/lib/hooks/use-translation'
import { getApiErrorKey } from '@/lib/utils/error-handler'

const ACTIVE_STATUSES = new Set(['queued', 'running', 'new', 'submitted'])

export function useExternalApiConnections() {
  return useQuery({
    queryKey: QUERY_KEYS.externalApiConnections,
    queryFn: externalApi.listConnections,
  })
}

export function useCreateExternalApiConnection() {
  const queryClient = useQueryClient()
  const { toast } = useToast()
  const { t } = useTranslation()

  return useMutation({
    mutationFn: (data: ExternalApiConnectionCreate) => externalApi.createConnection(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.externalApiConnections })
      toast({ title: t.common.success, description: t.common.saveSuccess })
    },
    onError: (error: unknown) => {
      toast({ title: t.common.error, description: getApiErrorKey(error, t.common.error), variant: 'destructive' })
    },
  })
}

export function useTestExternalApiConnection() {
  return useMutation({
    mutationFn: (connectionId: string) => externalApi.testConnection(connectionId),
  })
}

export function useExternalApiSources() {
  return useQuery({
    queryKey: QUERY_KEYS.externalApiSources,
    queryFn: externalApi.listSources,
  })
}

export function useCreateExternalApiSource() {
  const queryClient = useQueryClient()
  const { toast } = useToast()
  const { t } = useTranslation()

  return useMutation({
    mutationFn: (data: ExternalApiSourceCreate) => externalApi.createSource(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.externalApiSources })
      toast({ title: t.common.success, description: t.common.saveSuccess })
    },
    onError: (error: unknown) => {
      toast({ title: t.common.error, description: getApiErrorKey(error, t.common.error), variant: 'destructive' })
    },
  })
}

export function useCreateExternalApiTeamGrant() {
  const queryClient = useQueryClient()
  const { toast } = useToast()
  const { t } = useTranslation()

  return useMutation({
    mutationFn: ({ sourceId, data }: { sourceId: string; data: ExternalApiTeamGrantCreate }) =>
      externalApi.createTeamGrant(sourceId, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.externalApiSources })
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.externalApiAvailableSources(variables.data.team_id) })
      toast({ title: t.common.success, description: t.common.saveSuccess })
    },
    onError: (error: unknown) => {
      toast({ title: t.common.error, description: getApiErrorKey(error, t.common.error), variant: 'destructive' })
    },
  })
}

export function useAvailableExternalSources(teamId?: string | null) {
  return useQuery({
    queryKey: QUERY_KEYS.externalApiAvailableSources(teamId),
    queryFn: () => externalApi.listAvailableSources(teamId as string),
    enabled: Boolean(teamId),
  })
}

export function useSearchExternalSource() {
  return useMutation({
    mutationFn: ({ sourceId, data }: { sourceId: string; data: ExternalApiSearchRequest }) =>
      externalApi.search(sourceId, data),
  })
}

export function useFetchExternalItem() {
  return useMutation({
    mutationFn: ({ itemId, teamId }: { itemId: string; teamId: string }) =>
      externalApi.fetchItem(itemId, { team_id: teamId }),
  })
}

export function useReferenceExternalItem() {
  return useMutation({
    mutationFn: ({ itemId, notebookId }: { itemId: string; notebookId: string }) =>
      externalApi.referenceItem(itemId, notebookId),
  })
}

export function useSnapshotExternalItem() {
  return useMutation({
    mutationFn: ({ itemId, notebookId }: { itemId: string; notebookId: string }) =>
      externalApi.snapshotItem(itemId, { notebook_id: notebookId, embed: true }),
  })
}

export function useGenerateExternalOutput() {
  return useMutation({
    mutationFn: (data: ExternalApiOutputGenerateRequest) => externalApi.generateOutput(data),
  })
}

export function useExternalApiCommand(commandId?: string | null) {
  return useQuery({
    queryKey: QUERY_KEYS.externalApiCommand(commandId),
    queryFn: () => externalApi.commandStatus(commandId as string),
    enabled: Boolean(commandId),
    refetchInterval: (query) => {
      const status = query.state.data?.status
      return status && ACTIVE_STATUSES.has(status) ? 2000 : false
    },
    staleTime: 0,
  })
}

export function useExternalApiUsage(teamId?: string | null, month?: string | null) {
  return useQuery({
    queryKey: QUERY_KEYS.externalApiUsage(teamId, month),
    queryFn: () => externalApi.usage(teamId as string, month || undefined),
    enabled: Boolean(teamId),
  })
}
