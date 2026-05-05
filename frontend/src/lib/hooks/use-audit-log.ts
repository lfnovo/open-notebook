import { useQuery } from '@tanstack/react-query'
import { auditLogApi } from '@/lib/api/audit-log'

export function useAuditLog(params: {
  actor_id?: string
  action?: string
  target_id?: string
  limit?: number
  offset?: number
}) {
  return useQuery({
    queryKey: ['audit-log', params],
    queryFn: () => auditLogApi.list(params),
  })
}
