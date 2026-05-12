import { beforeEach, describe, expect, it, vi } from 'vitest'
import { queryClient } from '@/lib/api/query-client'
import { useAuthStore } from './auth-store'

vi.mock('@/lib/config', () => ({
  getApiUrl: vi.fn(async () => ''),
}))

describe('auth-store', () => {
  beforeEach(() => {
    localStorage.clear()
    queryClient.clear()
    useAuthStore.setState({
      isAuthenticated: false,
      token: null,
      username: null,
      role: null,
      displayName: null,
      status: null,
      isLoading: false,
      loadingAction: null,
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

  it('clears cached user data after a successful login', async () => {
    queryClient.setQueryData(['auth', 'me', 'old-user'], { username: 'old-user' })
    const fetchMock = vi.fn(async (url: string) => {
      if (url === '/api/auth/login') {
        return new Response(
          JSON.stringify({ success: true, token: 'jwt-token', username: 'new-user', message: 'ok' }),
          { status: 200, headers: { 'Content-Type': 'application/json' } }
        )
      }
      if (url === '/api/auth/me') {
        return new Response(
          JSON.stringify({
            id: 'app_user:new-user',
            username: 'new-user',
            display_name: 'New User',
            role: 'user',
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

    const ok = await useAuthStore.getState().login('new-user', 'password')

    expect(ok).toBe(true)
    expect(queryClient.getQueryData(['auth', 'me', 'old-user'])).toBeUndefined()
  })

  it('clears cached user data on logout', () => {
    queryClient.setQueryData(['teams', 'old-user', ''], { items: [] })
    useAuthStore.setState({
      isAuthenticated: true,
      token: 'old-token',
      username: 'old-user',
    })

    useAuthStore.getState().logout()

    expect(queryClient.getQueryData(['teams', 'old-user', ''])).toBeUndefined()
    expect(useAuthStore.getState().isAuthenticated).toBe(false)
  })

  it('releases WeChat loading state when web login is not configured', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () =>
        new Response(
          JSON.stringify({
            enabled: false,
            authorize_url: null,
            state: 'state',
            message: 'WeChat web login is not configured',
          }),
          { status: 200, headers: { 'Content-Type': 'application/json' } }
        )
      )
    )

    const ok = await useAuthStore.getState().startWeChatLogin()

    expect(ok).toBe(false)
    expect(useAuthStore.getState().isLoading).toBe(false)
    expect(useAuthStore.getState().loadingAction).toBe(null)
    expect(useAuthStore.getState().error).toBe('WeChat web login is not configured')
  })

  it('releases WeChat loading state after handing off to the redirect URL', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () =>
        new Response(
          JSON.stringify({
            enabled: true,
            authorize_url: '#wechat_redirect',
            state: 'state',
          }),
          { status: 200, headers: { 'Content-Type': 'application/json' } }
        )
      )
    )
    const ok = await useAuthStore.getState().startWeChatLogin()

    expect(ok).toBe(true)
    expect(useAuthStore.getState().isLoading).toBe(false)
    expect(useAuthStore.getState().loadingAction).toBe(null)
    expect(useAuthStore.getState().error).toBe(null)
  })
})
