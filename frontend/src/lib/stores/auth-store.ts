import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { queryClient } from '@/lib/api/query-client'
import { getApiUrl } from '@/lib/config'
import { AuthStatus, CurrentUserResponse, LoginResponse } from '@/lib/types/auth'

interface AuthState {
  isAuthenticated: boolean
  token: string | null
  username: string | null
  role: 'admin' | 'user' | null
  displayName: string | null
  status: 'active' | 'disabled' | null
  isLoading: boolean
  error: string | null
  lastAuthCheck: number | null
  isCheckingAuth: boolean
  hasHydrated: boolean
  authRequired: boolean | null
  authMethod: 'legacy' | 'database' | 'disabled' | null
  setHasHydrated: (state: boolean) => void
  checkAuthRequired: () => Promise<boolean>
  login: (username: string, password: string) => Promise<boolean>
  logout: () => void
  checkAuth: () => Promise<boolean>
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
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
      hasHydrated: false,
      authRequired: null,
      authMethod: null,

      setHasHydrated: (state: boolean) => {
        set({ hasHydrated: state })
      },

      checkAuthRequired: async () => {
        try {
          const apiUrl = await getApiUrl()
          const response = await fetch(`${apiUrl}/api/auth/status`, {
            cache: 'no-store',
          })

          if (!response.ok) {
            throw new Error(`Auth status check failed: ${response.status}`)
          }

          const data: AuthStatus = await response.json()
          const required = data.auth_enabled || false
          set({
            authRequired: required,
            authMethod: data.auth_method,
          })

          // If auth is not required, mark as authenticated
          if (!required) {
            set({
              isAuthenticated: true,
              token: 'not-required',
              username: 'guest',
              role: null,
              displayName: 'Guest',
              status: 'active',
            })
          }

          return required
        } catch (error) {
          console.error('Failed to check auth status:', error)

          if (error instanceof TypeError && error.message.includes('Failed to fetch')) {
            set({
              error: 'Unable to connect to server. Please check if the API is running.',
              authRequired: null,
            })
          } else {
            set({ authRequired: true })
          }

          throw error
        }
      },

      login: async (username: string, password: string) => {
        set({ isLoading: true, error: null })
        try {
          const apiUrl = await getApiUrl()

          const response = await fetch(`${apiUrl}/api/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password }),
          })

          if (!response.ok) {
            const errData = await response.json().catch(() => null)
            const message = errData?.detail || `Login failed (${response.status})`
            queryClient.clear()
            set({
              error: message,
              isLoading: false,
              isAuthenticated: false,
              token: null,
              username: null,
              role: null,
              displayName: null,
              status: null,
            })
            return false
          }

          const data: LoginResponse = await response.json()

          if (data.success && data.token) {
            let currentUser: CurrentUserResponse | null = null
            try {
              const meResponse = await fetch(`${apiUrl}/api/auth/me`, {
                method: 'GET',
                headers: {
                  'Authorization': `Bearer ${data.token}`,
                  'Content-Type': 'application/json',
                },
              })
              if (meResponse.ok) {
                currentUser = await meResponse.json()
              }
            } catch (profileError) {
              console.warn('Unable to load current user after login:', profileError)
            }

            queryClient.clear()
            set({
              isAuthenticated: true,
              token: data.token,
              username: currentUser?.username || data.username || username,
              role: currentUser?.role || null,
              displayName: currentUser?.display_name || currentUser?.username || data.username || username,
              status: currentUser?.status || 'active',
              isLoading: false,
              lastAuthCheck: Date.now(),
              error: null,
            })
            return true
          } else {
            queryClient.clear()
            set({
              error: data.message || 'Login failed',
              isLoading: false,
              isAuthenticated: false,
              token: null,
              username: null,
              role: null,
              displayName: null,
              status: null,
            })
            return false
          }
        } catch (error) {
          console.error('Network error during auth:', error)
          let errorMessage = 'Authentication failed'

          if (error instanceof TypeError && error.message.includes('Failed to fetch')) {
            errorMessage = 'Unable to connect to server. Please check if the API is running.'
          } else if (error instanceof Error) {
            errorMessage = `Network error: ${error.message}`
          } else {
            errorMessage = 'An unexpected error occurred during authentication'
          }

          queryClient.clear()
          set({
            error: errorMessage,
            isLoading: false,
            isAuthenticated: false,
            token: null,
            username: null,
            role: null,
            displayName: null,
            status: null,
          })
          return false
        }
      },

      logout: () => {
        queryClient.clear()
        set({
          isAuthenticated: false,
          token: null,
          username: null,
          role: null,
          displayName: null,
          status: null,
          error: null,
        })
      },

      checkAuth: async () => {
        const state = get()
        const { token, lastAuthCheck, isCheckingAuth, isAuthenticated } = state

        if (isCheckingAuth) {
          return isAuthenticated
        }

        if (!token) {
          return false
        }

        // If token is 'not-required', skip validation
        if (token === 'not-required') {
          return true
        }

        const now = Date.now()
        if (isAuthenticated && lastAuthCheck && (now - lastAuthCheck) < 30000) {
          return true
        }

        set({ isCheckingAuth: true })

        try {
          const apiUrl = await getApiUrl()

          const response = await fetch(`${apiUrl}/api/auth/me`, {
            method: 'GET',
            headers: {
              'Authorization': `Bearer ${token}`,
              'Content-Type': 'application/json',
            },
          })

          if (response.ok) {
            const user: CurrentUserResponse = await response.json()
            set({
              isAuthenticated: true,
              username: user.username || state.username,
              role: user.role || null,
              displayName: user.display_name || user.username || state.username,
              status: user.status || null,
              lastAuthCheck: now,
              isCheckingAuth: false,
            })
            return true
          } else {
            queryClient.clear()
            set({
              isAuthenticated: false,
              token: null,
              username: null,
              role: null,
              displayName: null,
              status: null,
              lastAuthCheck: null,
              isCheckingAuth: false,
            })
            return false
          }
        } catch (error) {
          console.error('checkAuth error:', error)
          queryClient.clear()
          set({
            isAuthenticated: false,
            token: null,
            username: null,
            role: null,
            displayName: null,
            status: null,
            lastAuthCheck: null,
            isCheckingAuth: false,
          })
          return false
        }
      },
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({
        token: state.token,
        isAuthenticated: state.isAuthenticated,
        username: state.username,
        role: state.role,
        displayName: state.displayName,
        status: state.status,
      }),
      onRehydrateStorage: () => (state) => {
        state?.setHasHydrated(true)
      },
    }
  )
)
