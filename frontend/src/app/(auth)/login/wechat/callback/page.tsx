'use client'

import { Suspense, useEffect, useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { AlertCircle } from 'lucide-react'
import { AuthPageShell } from '@/components/auth/AuthPageShell'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import { Button } from '@/components/ui/button'
import { useAuth } from '@/lib/hooks/use-auth'
import { useTranslation } from '@/lib/hooks/use-translation'

function WeChatCallbackContent() {
  const { t } = useTranslation()
  const router = useRouter()
  const searchParams = useSearchParams()
  const { finishWeChatLogin, isLoading, error } = useAuth()
  const [localError, setLocalError] = useState<string | null>(null)
  const missingCodeMessage = t.auth.weChatCallbackMissingCode
  const failedMessage = t.auth.weChatCallbackFailed

  useEffect(() => {
    const code = searchParams.get('code')
    const state = searchParams.get('state')
    if (!code) {
      setLocalError(missingCodeMessage)
      return
    }
    void finishWeChatLogin(code, state).then((success) => {
      if (!success) {
        setLocalError(failedMessage)
      }
    })
  }, [failedMessage, finishWeChatLogin, missingCodeMessage, searchParams])

  const message = localError || error

  return (
    <AuthPageShell
      title={t.auth.weChatCallbackTitle}
      description={t.auth.weChatCallbackDesc}
    >
      <div className="w-full max-w-[560px] px-7 py-7 text-stone-700 sm:px-8 sm:py-8">
        {!message && isLoading && (
          <div className="flex items-center justify-center py-8">
            <LoadingSpinner />
          </div>
        )}
        {message && (
          <div className="space-y-5">
            <div className="flex items-center gap-2 border border-red-200/80 bg-red-50/75 px-4 py-3 text-sm text-red-700">
              <AlertCircle className="h-4 w-4 flex-shrink-0" />
              {message}
            </div>
            <Button
              type="button"
              className="h-11 w-full rounded-none bg-[#6f6559] text-base font-medium text-white hover:bg-[#645a4e]"
              onClick={() => router.push('/login')}
            >
              {t.auth.backToLogin}
            </Button>
          </div>
        )}
      </div>
    </AuthPageShell>
  )
}

export default function WeChatCallbackPage() {
  return (
    <Suspense fallback={<LoadingSpinner />}>
      <WeChatCallbackContent />
    </Suspense>
  )
}
