import apiClient from './client'

export interface AuditLogEntry {
  id: string
  actor_id?: string | null
  actor_username?: string | null
  action: string
  target_type?: string | null
  target_id?: string | null
  metadata: Record<string, unknown>
  ip_address?: string | null
  user_agent?: string | null
  created: string
}

export interface AuditLogListResponse {
  items: AuditLogEntry[]
  limit: number
  offset: number
}

export const auditLogApi = {
  list: async (params?: {
    actor_id?: string
    action?: string
    target_id?: string
    limit?: number
    offset?: number
  }) => {
    const response = await apiClient.get<AuditLogListResponse>('/audit-log', { params })
    return response.data
  },
}
