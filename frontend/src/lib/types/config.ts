/**
 * Application configuration received from backend /api/config
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
