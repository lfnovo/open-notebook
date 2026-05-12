import apiClient from './client'

export type ExternalApiCapability = 'search' | 'fetch' | 'output'
export type ExternalApiConnectionTarget = 'source' | 'output'
export type ExternalOutputKind = 'markdown' | 'json' | 'file' | 'url'

export interface ExternalApiConnection {
  id: string
  name: string
  target_type: ExternalApiConnectionTarget
  base_url: string
  manifest?: Record<string, unknown> | null
  enabled: boolean
  timeout_seconds: number
  api_key_configured: boolean
  created_by?: string | null
  created: string
  updated: string
}

export interface ExternalApiConnectionCreate {
  name: string
  target_type?: ExternalApiConnectionTarget
  base_url: string
  api_key: string
  manifest?: Record<string, unknown> | null
  enabled?: boolean
  timeout_seconds?: number
}

export interface ExternalApiConnectionTestResult {
  ok: boolean
  status: string
  manifest?: Record<string, unknown> | null
  health?: Record<string, unknown> | null
  message?: string | null
}

export interface ExternalApiSource {
  id: string
  connection_id: string
  connection_name?: string | null
  name: string
  key: string
  description?: string | null
  capabilities: ExternalApiCapability[]
  config: Record<string, unknown>
  enabled: boolean
  created_by?: string | null
  created: string
  updated: string
}

export interface ExternalApiSourceCreate {
  connection_id: string
  name: string
  key: string
  description?: string
  capabilities: ExternalApiCapability[]
  config?: Record<string, unknown>
  enabled?: boolean
}

export interface ExternalApiTeamGrantCreate {
  team_id: string
  monthly_request_quota: number
  enabled?: boolean
}

export interface ExternalApiTeamGrant {
  id: string
  source_id: string
  source_name?: string | null
  team_id: string
  team_name?: string | null
  monthly_request_quota: number
  enabled: boolean
  created_by?: string | null
  created: string
  updated: string
}

export interface ExternalAvailableSource extends ExternalApiSource {
  grant_id: string
  team_id: string
  monthly_request_quota: number
  current_month_usage: number
}

export interface ExternalApiCommandResponse {
  command_id: string
  status: string
  message: string
}

export interface ExternalApiSearchRequest {
  team_id: string
  query: string
  limit?: number
  notebook_id?: string
  filters?: Record<string, unknown>
}

export interface ExternalApiFetchRequest {
  team_id: string
}

export interface ExternalApiSnapshotRequest {
  notebook_id: string
  embed?: boolean
}

export interface ExternalApiOutputGenerateRequest {
  team_id: string
  source_id: string
  prompt: string
  input_text?: string
  item_ids?: string[]
  output_kind?: ExternalOutputKind
  options?: Record<string, unknown>
}

export interface ExternalSourceItem {
  id: string
  source_id: string
  team_id: string
  external_id: string
  title: string
  summary?: string | null
  content_markdown?: string | null
  url?: string | null
  authors: string[]
  published_at?: string | null
  metadata: Record<string, unknown>
  fetched_at?: string | null
  created: string
  updated: string
}

export interface ExternalApiCommandStatus {
  job_id: string
  command_id: string
  status: string
  result?: {
    success?: boolean
    items?: ExternalSourceItem[]
    item_count?: number
    artifact?: Record<string, unknown>
    error_message?: string | null
    [key: string]: unknown
  } | null
  error_message?: string | null
  created?: string | null
  updated?: string | null
}

export interface ExternalApiUsageResponse {
  team_id: string
  month: string
  items: Array<{
    source_id: string
    source_name?: string | null
    operation: 'search' | 'fetch' | 'generate'
    month: string
    requests: number
    quota: number
  }>
}

export const externalApi = {
  listConnections: async () => {
    const response = await apiClient.get<{ items: ExternalApiConnection[] }>('/external-api/connections')
    return response.data
  },

  createConnection: async (data: ExternalApiConnectionCreate) => {
    const response = await apiClient.post<ExternalApiConnection>('/external-api/connections', data)
    return response.data
  },

  testConnection: async (connectionId: string) => {
    const response = await apiClient.post<ExternalApiConnectionTestResult>(
      '/external-api/connections/' + encodeURIComponent(connectionId) + '/test'
    )
    return response.data
  },

  listSources: async () => {
    const response = await apiClient.get<{ items: ExternalApiSource[] }>('/external-api/sources')
    return response.data
  },

  createSource: async (data: ExternalApiSourceCreate) => {
    const response = await apiClient.post<ExternalApiSource>('/external-api/sources', data)
    return response.data
  },

  createTeamGrant: async (sourceId: string, data: ExternalApiTeamGrantCreate) => {
    const response = await apiClient.post<ExternalApiTeamGrant>('/external-api/sources/' + encodeURIComponent(sourceId) + '/team-grants', data)
    return response.data
  },

  listTeamGrants: async (sourceId: string) => {
    const response = await apiClient.get<{ items: ExternalApiTeamGrant[] }>(
      '/external-api/sources/' + encodeURIComponent(sourceId) + '/team-grants'
    )
    return response.data
  },

  listAvailableSources: async (teamId: string) => {
    const response = await apiClient.get<{ items: ExternalAvailableSource[] }>('/external-api/available-sources', {
      params: { team_id: teamId },
    })
    return response.data
  },

  search: async (sourceId: string, data: ExternalApiSearchRequest) => {
    const response = await apiClient.post<ExternalApiCommandResponse>(
      '/external-api/sources/' + encodeURIComponent(sourceId) + '/search',
      data
    )
    return response.data
  },

  fetchItem: async (itemId: string, data: ExternalApiFetchRequest) => {
    const response = await apiClient.post<ExternalApiCommandResponse>(
      '/external-api/items/' + encodeURIComponent(itemId) + '/fetch',
      data
    )
    return response.data
  },

  referenceItem: async (itemId: string, notebookId: string) => {
    const response = await apiClient.post<ExternalSourceItem>(
      '/external-api/items/' + encodeURIComponent(itemId) + '/notebook-references',
      { notebook_id: notebookId }
    )
    return response.data
  },

  snapshotItem: async (itemId: string, data: ExternalApiSnapshotRequest) => {
    const response = await apiClient.post('/external-api/items/' + encodeURIComponent(itemId) + '/snapshot', data)
    return response.data
  },

  generateOutput: async (data: ExternalApiOutputGenerateRequest) => {
    const response = await apiClient.post<ExternalApiCommandResponse>('/external-api/outputs/generate', data)
    return response.data
  },

  commandStatus: async (commandId: string) => {
    const response = await apiClient.get<ExternalApiCommandStatus>(
      '/external-api/commands/' + encodeURIComponent(commandId)
    )
    return response.data
  },

  usage: async (teamId: string, month?: string) => {
    const response = await apiClient.get<ExternalApiUsageResponse>('/external-api/usage', {
      params: { team_id: teamId, month },
    })
    return response.data
  },
}
