export type DiscoveredSourceStatus = 'candidate' | 'created' | 'skipped' | 'error'

export interface DiscoveredSource {
  title: string
  url: string
  snippet: string
  score: number
  source_id?: string | null
  status: DiscoveredSourceStatus
  error?: string | null
}

export interface DiscoverSourcesRequest {
  query: string
  notebook_id: string
  limit?: number
  dry_run?: boolean
}

export interface DiscoverSourcesResponse {
  query: string
  provider: string
  notebook_id: string
  created_count: number
  skipped_count: number
  results: DiscoveredSource[]
}
