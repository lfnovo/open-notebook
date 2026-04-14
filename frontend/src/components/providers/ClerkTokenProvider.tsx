'use client'

import { useAuth } from '@clerk/nextjs'
import { useEffect } from 'react'
import { setTokenGetter } from '@/lib/api/client'

export function ClerkTokenProvider({ children }: { children: React.ReactNode }) {
  const { getToken } = useAuth()

  useEffect(() => {
    setTokenGetter(async () => getToken())
    return () => setTokenGetter(null)
  }, [getToken])

  return <>{children}</>
}
