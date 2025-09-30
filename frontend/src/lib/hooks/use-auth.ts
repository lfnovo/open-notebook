'use client'

import { useAuthStore } from '@/lib/stores/auth-store'
import { useRouter } from 'next/navigation'
import { useEffect } from 'react'

export function useAuth() {
  const router = useRouter()
  const { 
    isAuthenticated, 
    isLoading, 
    login, 
    logout, 
    checkAuth,
    error 
  } = useAuthStore()

  useEffect(() => {
    checkAuth()
    // Only run once on mount, not when checkAuth changes
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const handleLogin = async (password: string) => {
    const success = await login(password)
    if (success) {
      router.push('/notebooks')
    }
    return success
  }

  const handleLogout = () => {
    logout()
    router.push('/login')
  }

  return {
    isAuthenticated,
    isLoading,
    error,
    login: handleLogin,
    logout: handleLogout
  }
}