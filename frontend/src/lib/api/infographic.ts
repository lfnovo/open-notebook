import axios from 'axios'
import { apiClient } from './client'
import { getApiUrl } from '@/lib/config'

export interface InfographicColumn {
  icon: string
  title: string
  description: string
}

export interface InfographicHighlight {
  title: string
  subtitle?: string
  description: string
}

export interface InfographicResponse {
  source_id: string
  html?: string // kept for backward compat but no longer used for rendering
  header?: { title: string; subtitle: string; center_icon?: string }
  left_column?: InfographicColumn[]
  right_column?: InfographicColumn[]
  stat?: { value: string; label: string }
  highlights?: InfographicHighlight[]
}

// ── localStorage cache helpers ────────────────────────────────────────────────
const CACHE_PREFIX = 'infographic_cache_'

export function loadCachedInfographic(sourceId: string): InfographicResponse | null {
  try {
    const key = CACHE_PREFIX + sourceId
    const raw = localStorage.getItem(key)
    if (!raw) {
      console.log('[InfographicCache] MISS for', sourceId)
      return null
    }
    const parsed = JSON.parse(raw) as InfographicResponse
    console.log('[InfographicCache] HIT for', sourceId, '— html length:', parsed.html?.length)
    return parsed
  } catch (e) {
    console.warn('[InfographicCache] load error:', e)
    return null
  }
}

export function saveCachedInfographic(sourceId: string, data: InfographicResponse) {
  try {
    const key = CACHE_PREFIX + sourceId
    const serialized = JSON.stringify(data)
    console.log('[InfographicCache] Saving for', sourceId, '— size:', serialized.length, 'bytes')
    localStorage.setItem(key, serialized)
    // Verify it was actually saved
    const verify = localStorage.getItem(key)
    if (verify) {
      console.log('[InfographicCache] Save verified OK for', sourceId)
    } else {
      console.error('[InfographicCache] Save FAILED (item not found after set) for', sourceId)
    }
  } catch (e) {
    console.error('[InfographicCache] Save error for', sourceId, ':', e)
    // If quota exceeded, clear old infographic caches and retry
    try {
      const keysToRemove: string[] = []
      for (let i = 0; i < localStorage.length; i++) {
        const k = localStorage.key(i)
        if (k && k.startsWith(CACHE_PREFIX) && k !== CACHE_PREFIX + sourceId) {
          keysToRemove.push(k)
        }
      }
      keysToRemove.forEach(k => localStorage.removeItem(k))
      console.log('[InfographicCache] Cleared', keysToRemove.length, 'old cache entries, retrying...')
      localStorage.setItem(CACHE_PREFIX + sourceId, JSON.stringify(data))
      console.log('[InfographicCache] Retry save OK for', sourceId)
    } catch (e2) {
      console.error('[InfographicCache] Retry save also failed:', e2)
    }
  }
}

// ── Dedicated no-timeout axios instance ──────────────────────────────────────
const infographicClient = axios.create({
  timeout: 0,
  headers: { 'Content-Type': 'application/json' },
  withCredentials: false,
})

infographicClient.interceptors.request.use(async (config) => {
  const apiUrl = await getApiUrl()
  config.baseURL = `${apiUrl}/api`
  if (typeof window !== 'undefined') {
    const authStorage = localStorage.getItem('auth-storage')
    if (authStorage) {
      try {
        const { state } = JSON.parse(authStorage)
        if (state?.token) config.headers.Authorization = `Bearer ${state.token}`
      } catch (_) {}
    }
  }
  return config
})

export const infographicApi = {
  generate: async (sourceId: string): Promise<InfographicResponse> => {
    const response = await infographicClient.post<InfographicResponse>(
      `/sources/${encodeURIComponent(sourceId)}/infographic`,
      { model_name: 'qwen3', temperature: 0.3 }
    )
    return response.data
  },

  getStatus: async (sourceId: string): Promise<{ status: string | null; message?: string }> => {
    try {
      const response = await apiClient.get(`/sources/${encodeURIComponent(sourceId)}/status`)
      return response.data
    } catch {
      return { status: null }
    }
  },
}
