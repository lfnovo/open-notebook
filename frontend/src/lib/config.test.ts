import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { getApiUrl, resetConfig } from './config'

// Mock global fetch
const fetchMock = vi.fn()
global.fetch = fetchMock

describe('Config Priority', () => {
  const originalEnv = process.env

  beforeEach(() => {
    vi.resetModules()
    resetConfig()
    process.env = { ...originalEnv }
    fetchMock.mockReset()
  })

  afterEach(() => {
    process.env = originalEnv
  })

  it('should prioritize runtime config over everything else', async () => {
    // Setup: Env var set, Runtime config returns explicit value
    process.env.NEXT_PUBLIC_API_URL = 'http://env-url.com'
    
    fetchMock.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ apiUrl: 'http://runtime-url.com' }),
    })

    // Mock the second fetch call (api/config check)
    fetchMock.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ version: '1.0.0' }),
    })

    const url = await getApiUrl()
    expect(url).toBe('http://runtime-url.com')
  })

  it('should fall back to env var if runtime config returns empty/null', async () => {
    // Setup: Env var set, Runtime config returns empty string (simulating not set)
    process.env.NEXT_PUBLIC_API_URL = 'http://env-url.com'
    
    // First fetch: /config returns empty apiUrl
    fetchMock.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ apiUrl: '' }),
    })

    // Second fetch: api/config check using env url
    fetchMock.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ version: '1.0.0' }),
    })

    const url = await getApiUrl()
    expect(url).toBe('http://env-url.com')
  })

  it('should use default (relative path) if both runtime and env are missing', async () => {
    // Setup: Env var NOT set, Runtime config returns empty
    delete process.env.NEXT_PUBLIC_API_URL
    
    // First fetch: /config returns empty
    fetchMock.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ apiUrl: '' }),
    })

    // Second fetch: api/config check using default relative path
    fetchMock.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ version: '1.0.0' }),
    })

    const url = await getApiUrl()
    expect(url).toBe('')
  })
})
