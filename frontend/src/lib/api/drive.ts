import apiClient from './client'
import {
  DriveAuthUrlResponse,
  DriveDisconnectResponse,
  DriveFileListResponse,
  DriveImportRequest,
  DriveStatusResponse,
} from '@/lib/types/drive'
import { SourceResponse } from '@/lib/types/api'

export const driveApi = {
  getAuthUrl: async () => {
    const response = await apiClient.get<DriveAuthUrlResponse>('/drive/auth-url')
    return response.data
  },

  getStatus: async () => {
    const response = await apiClient.get<DriveStatusResponse>('/drive/status')
    return response.data
  },

  disconnect: async () => {
    const response = await apiClient.delete<DriveDisconnectResponse>('/drive/disconnect')
    return response.data
  },

  listFiles: async (params: { query?: string; page_token?: string }) => {
    const response = await apiClient.get<DriveFileListResponse>('/drive/files', { params })
    return response.data
  },

  importFile: async (data: DriveImportRequest) => {
    const response = await apiClient.post<SourceResponse>('/drive/import', data)
    return response.data
  },
}
