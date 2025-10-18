import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { settingsApi } from '@/lib/api/settings'
import { QUERY_KEYS } from '@/lib/api/query-client'
import { useToast } from '@/lib/hooks/use-toast'
import { SettingsResponse } from '@/lib/types/api'

export function useSettings() {
  return useQuery({
    queryKey: QUERY_KEYS.settings,
    queryFn: () => settingsApi.get(),
  })
}

export function useUpdateSettings() {
  const queryClient = useQueryClient()
  const { toast } = useToast()

  return useMutation({
    mutationFn: (data: Partial<SettingsResponse>) => settingsApi.update(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.settings })
      toast({
        title: 'Success',
        description: 'Settings updated successfully',
      })
    },
    onError: () => {
      toast({
        title: 'Error',
        description: 'Failed to update settings',
        variant: 'destructive',
      })
    },
  })
}