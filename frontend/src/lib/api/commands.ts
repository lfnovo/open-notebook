import apiClient from './client'
import { CommandJobResponse, CommandJobStatusResponse } from '@/lib/types/commands'

export const commandsApi = {
  submit: async <TInput extends Record<string, unknown>>(
    command: string,
    app: string,
    input: TInput
  ) => {
    const response = await apiClient.post<CommandJobResponse>('/commands/jobs', {
      command,
      app,
      input,
    })
    return response.data
  },

  getStatus: async <TResult = Record<string, unknown>>(jobId: string) => {
    const response = await apiClient.get<CommandJobStatusResponse<TResult>>(
      `/commands/jobs/${jobId}`
    )
    return response.data
  },
}
