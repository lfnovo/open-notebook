import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useAuthStore } from './auth-store'

vi.mock('@/lib/config', () => ({
  getApiUrl: vi.fn(async () => ''),
}))

describe('auth-store', () => {
  beforeEach(() => {
    localStorage.clear()
    useAuthStore.setState({
      isAuthenticated: false,
      token: null,
      username: null,
      role: null,
      displayName: null,
      status: null,
      isLoading: false,
      error: null,
      lastAuthCheck: null,
      isCheckingAuth: false,
      hasHydrated: true,
      authRequired: null,
      authMethod: null,
    })
    vi.restoreAllMocks()
  })

  it('loads current user role immediately after login', async () => {
    const fetchMock = vi.fn(async (url: string) => {
      if (url === '/api/auth/login') {
        return new Response(
          JSON.stringify({ success: true, token: 'jwt-token', username: 'admin', message: 'ok' }),
          { status: 200, headers: { 'Content-Type': 'application/json' } }
        )
      }
      if (url === '/api/auth/me') {
        return new Response(
          JSON.stringify({
            id: 'app_user:admin',
            username: 'admin',
            display_name: 'Admin',
            role: 'admin',
            status: 'active',
            created: '',
            updated: '',
          }),
          { status: 200, headers: { 'Content-Type': 'application/json' } }
        )
      }
      return new Response('{}', { status: 404 })
    })
    vi.stubGlobal('fetch', fetchMock)

    const ok = await useAuthStore.getState().login('admin', 'admin')

    expect(ok).toBe(true)
    expect(fetchMock).toHaveBeenCalledWith('/api/auth/me', expect.objectContaining({
      headers: expect.objectContaining({ Authorization: 'Bearer jwt-token' }),
    }))
    expect(useAuthStore.getState().role).toBe('admin')
    expect(useAuthStore.getState().displayName).toBe('Admin')
  })
})
