/** Matches api/models.py Drive* schemas (api/routers/drive.py). */

export interface DriveAuthUrlResponse {
  auth_url: string
}

export interface DriveStatusResponse {
  connected: boolean
  account_email?: string | null
}

export interface DriveDisconnectResponse {
  message: string
}

export interface DriveFile {
  id: string
  name: string
  mime_type: string
  modified_time?: string | null
  icon_link?: string | null
}

export interface DriveFileListResponse {
  files: DriveFile[]
  next_page_token?: string | null
}

export interface DriveImportRequest {
  file_id: string
  notebook_id: string
}
