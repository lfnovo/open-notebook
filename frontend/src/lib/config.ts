/**
 * Runtime configuration for the frontend.
 * This allows the same Docker image to work in different environments.
 */

// Build timestamp for debugging - set at build time
const BUILD_TIME = new Date().toISOString()

interface AppConfig {
  apiUrl: string
  version: string
  buildTime: string
  latestVersion?: string | null
  hasUpdate?: boolean
}

let config: AppConfig | null = null
let configPromise: Promise<AppConfig> | null = null

/**
 * Get the API URL to use for requests.
 *
 * Priority:
 * 1. Runtime config from API server (/api/config endpoint)
 * 2. Environment variable (NEXT_PUBLIC_API_URL)
 * 3. Default fallback (http://localhost:5055)
 */
export async function getApiUrl(): Promise<string> {
  // If we already have config, return it
  if (config) {
    return config.apiUrl
  }

  // If we're already fetching, wait for that
  if (configPromise) {
    const cfg = await configPromise
    return cfg.apiUrl
  }

  // Start fetching config
  configPromise = fetchConfig()
  const cfg = await configPromise
  return cfg.apiUrl
}

/**
 * Get the full configuration.
 */
export async function getConfig(): Promise<AppConfig> {
  if (config) {
    return config
  }

  if (configPromise) {
    return await configPromise
  }

  configPromise = fetchConfig()
  return await configPromise
}

/**
 * Fetch configuration from the API or use defaults.
 */
async function fetchConfig(): Promise<AppConfig> {
  console.log('🔧 [Config] Starting configuration detection...')
  console.log('🔧 [Config] Build time:', BUILD_TIME)

  // Try to get from environment variable first (for development)
  const envApiUrl = process.env.NEXT_PUBLIC_API_URL
  console.log('🔧 [Config] NEXT_PUBLIC_API_URL from build:', envApiUrl || '(not set)')

  // Smart default: infer API URL from current frontend URL
  // If frontend is at http://10.20.30.20:8502, API should be at http://10.20.30.20:5055
  let defaultApiUrl = 'http://localhost:5055'

  if (typeof window !== 'undefined') {
    const hostname = window.location.hostname
    const protocol = window.location.protocol
    console.log('🔧 [Config] Current frontend URL:', `${protocol}//${hostname}${window.location.port ? ':' + window.location.port : ''}`)

    // If not localhost, use the same hostname with port 5055
    if (hostname !== 'localhost' && hostname !== '127.0.0.1') {
      defaultApiUrl = `${protocol}//${hostname}:5055`
      console.log('🔧 [Config] Detected remote hostname, using:', defaultApiUrl)
    } else {
      console.log('🔧 [Config] Detected localhost, using:', defaultApiUrl)
    }
  }

  // Use env var if available, otherwise smart default
  const baseUrl = envApiUrl || defaultApiUrl
  console.log('🔧 [Config] Final base URL to try:', baseUrl)

  try {
    console.log('🔧 [Config] Fetching runtime config from:', `${baseUrl}/api/config`)
    // Try to fetch runtime config from API
    const response = await fetch(`${baseUrl}/api/config`, {
      cache: 'no-store',
    })

    if (response.ok) {
      const data = await response.json()
      config = {
        apiUrl: data.apiUrl || baseUrl,
        version: data.version || 'unknown',
        buildTime: BUILD_TIME,
        latestVersion: data.latestVersion || null,
        hasUpdate: data.hasUpdate || false,
      }
      console.log('✅ [Config] Successfully loaded API config:', config)
      return config
    } else {
      console.error('❌ [Config] API config request failed with status:', response.status)
    }
  } catch (error) {
    console.error('❌ [Config] Failed to fetch runtime config from', baseUrl, ':', error)
  }

  // If fetching config fails, use the baseUrl we determined
  config = {
    apiUrl: baseUrl,
    version: 'unknown',
    buildTime: BUILD_TIME,
  }

  console.warn('⚠️ [Config] Using fallback API config:', config)
  return config
}

/**
 * Reset the configuration cache (useful for testing).
 */
export function resetConfig(): void {
  config = null
  configPromise = null
}
