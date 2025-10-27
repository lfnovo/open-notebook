/**
 * Runtime configuration for the frontend.
 * This allows the same Docker image to work in different environments.
 */

import { AppConfig, BackendConfigResponse } from '@/lib/types/config'

// Build timestamp for debugging - set at build time
const BUILD_TIME = new Date().toISOString()

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

  // STEP 1: Try to get runtime config from Next.js server-side endpoint
  // This allows API_URL to be set at runtime (not baked into build)
  // Note: Endpoint is at /config (not /api/config) to avoid reverse proxy conflicts
  let runtimeApiUrl: string | null = null
  try {
    console.log('🔧 [Config] Attempting to fetch runtime config from /config endpoint...')
    const runtimeResponse = await fetch('/config', {
      cache: 'no-store',
    })
    if (runtimeResponse.ok) {
      const runtimeData = await runtimeResponse.json()
      runtimeApiUrl = runtimeData.apiUrl
      console.log('✅ [Config] Runtime API URL from server:', runtimeApiUrl)
    } else {
      console.log('⚠️ [Config] Runtime config endpoint returned status:', runtimeResponse.status)
    }
  } catch (error) {
    console.log('⚠️ [Config] Could not fetch runtime config:', error)
  }

  // STEP 2: Fallback to build-time environment variable
  const envApiUrl = process.env.NEXT_PUBLIC_API_URL
  console.log('🔧 [Config] NEXT_PUBLIC_API_URL from build:', envApiUrl || '(not set)')

  // STEP 3: Smart default - infer API URL from current frontend URL
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

  // Priority: Runtime config > Build-time env var > Smart default
  const baseUrl = runtimeApiUrl || envApiUrl || defaultApiUrl
  console.log('🔧 [Config] Final base URL to try:', baseUrl)
  console.log('🔧 [Config] Selection priority: runtime=' + (runtimeApiUrl ? '✅' : '❌') +
              ', build-time=' + (envApiUrl ? '✅' : '❌') +
              ', smart-default=' + (!runtimeApiUrl && !envApiUrl ? '✅' : '❌'))

  try {
    console.log('🔧 [Config] Fetching backend config from:', `${baseUrl}/api/config`)
    // Try to fetch runtime config from backend API
    const response = await fetch(`${baseUrl}/api/config`, {
      cache: 'no-store',
    })

    if (response.ok) {
      const data: BackendConfigResponse = await response.json()
      config = {
        apiUrl: baseUrl, // Use baseUrl from runtime-config (Python no longer returns this)
        version: data.version || 'unknown',
        buildTime: BUILD_TIME,
        latestVersion: data.latestVersion || null,
        hasUpdate: data.hasUpdate || false,
        dbStatus: data.dbStatus, // Can be undefined for old backends
      }
      console.log('✅ [Config] Successfully loaded API config:', config)
      return config
    } else {
      // Don't log error here - ConnectionGuard will display it
      throw new Error(`API config endpoint returned status ${response.status}`)
    }
  } catch (error) {
    // Don't log error here - ConnectionGuard will display it with proper UI
    throw error
  }
}

/**
 * Reset the configuration cache (useful for testing).
 */
export function resetConfig(): void {
  config = null
  configPromise = null
}
