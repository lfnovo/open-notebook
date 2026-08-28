import apiClient from './client'
import { UsagePeriod, UsageSummary } from '@/lib/types/usage'

export const usageApi = {
  getSummary: async (period: UsagePeriod = 'month') => {
    const response = await apiClient.get<UsageSummary>('/usage/summary', {
      params: { period },
    })
    return response.data
  },
}
