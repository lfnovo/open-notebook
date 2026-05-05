import { useQuery } from '@tanstack/react-query'
import { teamsApi } from '@/lib/api/teams'
import { QUERY_KEYS } from '@/lib/api/query-client'

export function useTeams() {
  return useQuery({
    queryKey: QUERY_KEYS.teams,
    queryFn: () => teamsApi.list(),
  })
}
