import { useCallback } from 'react'
import { useAuthStore } from '@/lib/stores/auth-store'
import { useRouter } from 'next/navigation'

export function useAuth() {
  const {
    login: storeLogin,
    startWeChatLogin,
    completeWeChatLogin,
    logout: storeLogout,
    isLoading,
    loadingAction,
    error,
    isAuthenticated,
    username,
    requiresProfileCompletion,
  } = useAuthStore()
  const isPasswordLoading = isLoading && loadingAction === 'password'
  const isWeChatLoading = isLoading && loadingAction === 'wechat'
  const router = useRouter()

  const login = useCallback(
    async (username: string, password: string) => {
      const success = await storeLogin(username, password)
      if (success) {
        router.push('/notebooks')
      }
      return success
    },
    [storeLogin, router]
  )

  const loginWithWeChat = useCallback(async () => {
    return await startWeChatLogin()
  }, [startWeChatLogin])

  const finishWeChatLogin = useCallback(
    async (code: string, state: string | null) => {
      const success = await completeWeChatLogin(code, state)
      if (success) {
        const nextPath = useAuthStore.getState().requiresProfileCompletion
          ? '/settings/profile?complete=1'
          : '/notebooks'
        router.push(nextPath)
      }
      return success
    },
    [completeWeChatLogin, router]
  )

  const logout = useCallback(() => {
    storeLogout()
    router.push('/')
  }, [storeLogout, router])

  return {
    login,
    loginWithWeChat,
    finishWeChatLogin,
    logout,
    isLoading,
    isPasswordLoading,
    isWeChatLoading,
    error,
    isAuthenticated,
    username,
    requiresProfileCompletion,
  }
}
