/**
 * Backend configuration response from Python API /api/config endpoint.
 * Note: apiUrl is determined by the Next.js runtime-config endpoint,
 * not returned by the Python backend.
 */
export interface BackendConfigResponse {
  version: string
  latestVersion?: string | null
  hasUpdate?: boolean
  dbStatus?: "online" | "offline"
}

/**
 * Complete application configuration used by the frontend.
 * This is constructed from the backend response + runtime-config.
 */
export interface AppConfig {
  apiUrl: string
  version: string
  buildTime: string
  latestVersion?: string | null
  hasUpdate?: boolean
  dbStatus?: "online" | "offline"
}

/**
 * Connection error state
 */
export interface ConnectionError {
  type: "api-unreachable" | "database-offline"
  details?: {
    message?: string
    technicalMessage?: string
    stack?: string
    attemptedUrl?: string
  }
}
