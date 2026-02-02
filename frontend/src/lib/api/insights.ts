import apiClient from './client'

export interface SourceInsightResponse {
  id: string
  source_id: string
  insight_type: string
  content: string
  created: string
  updated: string
}

export interface CreateSourceInsightRequest {
  transformation_id: string
}

export interface InsightCreationResponse {
  status: 'pending'
  message: string
  source_id: string
  transformation_id: string
  command_id?: string
}

export interface CommandJobStatusResponse {
  job_id: string
  status: string
  result?: Record<string, unknown>
  error_message?: string
}

export const insightsApi = {
  listForSource: async (sourceId: string) => {
    const response = await apiClient.get<SourceInsightResponse[]>(`/sources/${sourceId}/insights`)
    return response.data
  },

  get: async (insightId: string) => {
    const response = await apiClient.get<SourceInsightResponse>(`/insights/${insightId}`)
    return response.data
  },

  create: async (sourceId: string, data: CreateSourceInsightRequest) => {
    const response = await apiClient.post<InsightCreationResponse>(
      `/sources/${sourceId}/insights`,
      data
    )
    return response.data
  },

  delete: async (insightId: string) => {
    await apiClient.delete(`/insights/${insightId}`)
  },

  getCommandStatus: async (commandId: string) => {
    const response = await apiClient.get<CommandJobStatusResponse>(
      `/commands/jobs/${commandId}`
    )
    return response.data
  },

  /**
   * Poll command status until completed or failed.
   * Returns true if completed successfully, false if failed.
   */
  waitForCommand: async (
    commandId: string,
    options?: { maxAttempts?: number; intervalMs?: number }
  ): Promise<boolean> => {
    const maxAttempts = options?.maxAttempts ?? 60 // Default 60 attempts
    const intervalMs = options?.intervalMs ?? 2000 // Default 2 seconds

    for (let i = 0; i < maxAttempts; i++) {
      try {
        const status = await insightsApi.getCommandStatus(commandId)
        if (status.status === 'completed') {
          return true
        }
        if (status.status === 'failed' || status.status === 'canceled') {
          console.error('Command failed:', status.error_message)
          return false
        }
        // Still running, wait and retry
        await new Promise(resolve => setTimeout(resolve, intervalMs))
      } catch (error) {
        console.error('Error checking command status:', error)
        // Continue polling on error
        await new Promise(resolve => setTimeout(resolve, intervalMs))
      }
    }
    // Timeout
    console.warn('Command polling timed out')
    return false
  }
}