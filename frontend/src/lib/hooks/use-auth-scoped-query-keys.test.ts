import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, renderHook, waitFor } from '@testing-library/react'
import { ReactNode, createElement } from 'react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { authApi } from '@/lib/api/auth'
import { teamsApi } from '@/lib/api/teams'
import { useAuthStore } from '@/lib/stores/auth-store'
import { CurrentUserResponse } from '@/lib/types/auth'
import { TeamListResponse } from '@/lib/api/teams'
import { profileQueryKey, useProfile } from './use-profile'
import { teamsQueryKey, useTeams } from './use-teams'

vi.mock('@/lib/api/auth', () => ({
  authApi: {
    me: vi.fn(),
    updateMe: vi.fn(),
  },
}))

vi.mock('@/lib/api/teams', () => ({
  teamsApi: {
    list: vi.fn(),
  },
}))

function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 5 * 60 * 1000,
        retry: false,
      },
    },
  })
}

function createWrapper(queryClient: QueryClient) {
  return function Wrapper({ children }: { children: ReactNode }) {
    return createElement(QueryClientProvider, { client: queryClient }, children)
  }
}

function setAuthenticatedUser(username: string) {
  act(() => {
    useAuthStore.setState({
      isAuthenticated: true,
      token: `${username}-token`,
      username,
      role: 'user',
      displayName: username,
      status: 'active',
    })
  })
}

function profile(username: string): CurrentUserResponse {
  return {
    username,
    display_name: username,
    role: 'user',
    status: 'active',
    created: '2026-05-05T00:00:00Z',
    updated: '2026-05-05T00:00:00Z',
  }
}

function teamList(name: string): TeamListResponse {
  return {
    items: [
      {
        id: `team:${name}`,
        slug: name,
        name,
        type: 'workspace',
        created: '2026-05-05T00:00:00Z',
        updated: '2026-05-05T00:00:00Z',
        member_count: 1,
        share_count: 0,
        current_user_role: 'member',
        can_manage: false,
      },
    ],
    total: 1,
    limit: 50,
    offset: 0,
  }
}

afterEach(() => {
  vi.clearAllMocks()
  act(() => {
    useAuthStore.setState({
      isAuthenticated: false,
      token: null,
      username: null,
      role: null,
      displayName: null,
      status: null,
    })
  })
})

describe('auth-scoped query keys', () => {
  it('scopes profile cache by the current user identity', () => {
    expect(profileQueryKey('alice')).toEqual(['auth', 'me', 'alice'])
    expect(profileQueryKey('bob')).toEqual(['auth', 'me', 'bob'])
    expect(profileQueryKey('alice')).not.toEqual(profileQueryKey('bob'))
  })

  it('scopes team list cache by the current user identity and search text', () => {
    expect(teamsQueryKey('alice', '')).toEqual(['teams', 'alice', ''])
    expect(teamsQueryKey('bob', '')).toEqual(['teams', 'bob', ''])
    expect(teamsQueryKey('alice', 'ops')).toEqual(['teams', 'alice', 'ops'])
    expect(teamsQueryKey('alice', '')).not.toEqual(teamsQueryKey('bob', ''))
  })

  it('reloads profile data when the authenticated user changes', async () => {
    const queryClient = createTestQueryClient()
    const wrapper = createWrapper(queryClient)

    vi.mocked(authApi.me)
      .mockResolvedValueOnce(profile('alice'))
      .mockResolvedValueOnce(profile('bob'))

    setAuthenticatedUser('alice')
    const aliceHook = renderHook(() => useProfile(), { wrapper })
    await waitFor(() => expect(aliceHook.result.current.data?.username).toBe('alice'))
    expect(authApi.me).toHaveBeenCalledTimes(1)
    aliceHook.unmount()

    setAuthenticatedUser('bob')
    const bobHook = renderHook(() => useProfile(), { wrapper })
    await waitFor(() => expect(bobHook.result.current.data?.username).toBe('bob'))
    expect(authApi.me).toHaveBeenCalledTimes(2)
    bobHook.unmount()
  })

  it('reloads team data when the authenticated user changes', async () => {
    const queryClient = createTestQueryClient()
    const wrapper = createWrapper(queryClient)

    vi.mocked(teamsApi.list)
      .mockResolvedValueOnce(teamList('alice-team'))
      .mockResolvedValueOnce(teamList('bob-team'))

    setAuthenticatedUser('alice')
    const aliceHook = renderHook(() => useTeams(), { wrapper })
    await waitFor(() => expect(aliceHook.result.current.data?.items[0]?.name).toBe('alice-team'))
    expect(teamsApi.list).toHaveBeenCalledTimes(1)
    aliceHook.unmount()

    setAuthenticatedUser('bob')
    const bobHook = renderHook(() => useTeams(), { wrapper })
    await waitFor(() => expect(bobHook.result.current.data?.items[0]?.name).toBe('bob-team'))
    expect(teamsApi.list).toHaveBeenCalledTimes(2)
    bobHook.unmount()
  })
})
