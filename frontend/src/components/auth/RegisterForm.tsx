'use client'

import { useState, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { MessageCircle } from 'lucide-react'
import { useAuth } from '@/lib/hooks/use-auth'
import { useTranslation } from '@/lib/hooks/use-translation'
import { getApiUrl } from '@/lib/config'

export function RegisterForm() {
  const { t } = useTranslation()
  const router = useRouter()
  const { loginWithWeChat, isWeChatLoading, error: authError } = useAuth()

  const [email, setEmail] = useState('')
  const [code, setCode] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [isSendingCode, setIsSendingCode] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)
  const [countdown, setCountdown] = useState(0)
  const displayedAuthError =
    authError === 'WeChat web login is not configured'
      ? t.auth.weChatNotConfigured
      : authError
  const displayedError = error || displayedAuthError

  const sendCode = useCallback(async () => {
    if (!email) return
    setIsSendingCode(true)
    setError(null)
    try {
      const apiUrl = await getApiUrl()
      const res = await fetch(`${apiUrl}/api/auth/send-code`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, purpose: 'register' }),
      })
      const data = await res.json()
      if (res.ok && data.success) {
        setCountdown(60)
        const timer = setInterval(() => {
          setCountdown((c) => {
            if (c <= 1) { clearInterval(timer); return 0 }
            return c - 1
          })
        }, 1000)
      } else {
        setError(data.message || t.auth.sendCodeError || 'Failed to send code')
      }
    } catch {
      setError('Network error. Please try again.')
    } finally {
      setIsSendingCode(false)
    }
  }, [email, t])

  const handleSubmit = useCallback(async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    if (password.length < 6) {
      setError(t.auth.registerPasswordTooShort)
      return
    }
    if (password !== confirmPassword) {
      setError(t.auth.registerPasswordMismatch)
      return
    }

    setIsLoading(true)
    try {
      const apiUrl = await getApiUrl()
      const res = await fetch(`${apiUrl}/api/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, code, password }),
      })
      const data = await res.json()
      if (res.ok && data.success) {
        setSuccess(true)
        setTimeout(() => {
          router.push('/login')
        }, 1500)
      } else {
        setError(data.message || t.auth.registerError)
      }
    } catch {
      setError('Network error. Please try again.')
    } finally {
      setIsLoading(false)
    }
  }, [email, code, password, confirmPassword, router, t])

  if (success) {
    return (
      <div className="w-full max-w-md rounded-2xl border border-stone-200/60 bg-white/80 p-8 text-center shadow-xl backdrop-blur-sm">
        <div className="mb-4 text-5xl">✓</div>
        <h2 className="mb-2 text-2xl font-light text-stone-700">{t.auth.registerSuccess}</h2>
        <p className="text-stone-500">{t.auth.emailSent}</p>
        <p className="mt-4 text-sm text-stone-400">
          Redirecting to login...
        </p>
      </div>
    )
  }

  return (
      <div className="w-full max-w-md rounded-2xl border border-stone-200/60 bg-white/80 p-8 shadow-xl backdrop-blur-sm">
        <div className="mb-8 text-center">
          <h1 className="mb-2 text-3xl font-light text-stone-700">{t.auth.registerTitle}</h1>
          <p className="text-stone-500">{t.auth.registerDesc}</p>
        </div>

        {displayedError && (
          <div className="mb-4 rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-600">
            {displayedError}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4" aria-label="Register form">
          <div>
            <label className="mb-1 block text-sm font-medium text-stone-600">{t.auth.registerEmailPlaceholder}</label>
            <div className="flex gap-2">
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder={t.auth.registerEmailPlaceholder}
                required
                className="flex-1 rounded-lg border border-stone-300 bg-white/60 px-4 py-3 text-stone-700 placeholder-stone-400 shadow-sm transition focus:border-stone-400 focus:outline-none focus:ring-1 focus:ring-stone-400"
              />
              <button
                type="button"
                onClick={sendCode}
                disabled={isSendingCode || !email || countdown > 0}
                className="shrink-0 rounded-lg border border-stone-300 bg-stone-50 px-3 py-3 text-sm font-medium text-stone-600 transition hover:bg-stone-100 disabled:opacity-50"
              >
                {countdown > 0 ? `${countdown}s` : isSendingCode ? t.auth.sendingCode : t.auth.sendCode}
              </button>
            </div>
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium text-stone-600">{t.auth.registerCodePlaceholder}</label>
            <input
              type="text"
              value={code}
              onChange={(e) => setCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
              placeholder={t.auth.registerCodePlaceholder}
              required
              className="w-full rounded-lg border border-stone-300 bg-white/60 px-4 py-3 text-stone-700 placeholder-stone-400 shadow-sm transition focus:border-stone-400 focus:outline-none focus:ring-1 focus:ring-stone-400"
            />
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium text-stone-600">{t.auth.registerPasswordPlaceholder}</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder={t.auth.registerPasswordPlaceholder}
              required
              minLength={6}
              className="w-full rounded-lg border border-stone-300 bg-white/60 px-4 py-3 text-stone-700 placeholder-stone-400 shadow-sm transition focus:border-stone-400 focus:outline-none focus:ring-1 focus:ring-stone-400"
            />
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium text-stone-600">{t.auth.registerConfirmPasswordPlaceholder}</label>
            <input
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              placeholder={t.auth.registerConfirmPasswordPlaceholder}
              required
              minLength={6}
              className="w-full rounded-lg border border-stone-300 bg-white/60 px-4 py-3 text-stone-700 placeholder-stone-400 shadow-sm transition focus:border-stone-400 focus:outline-none focus:ring-1 focus:ring-stone-400"
            />
          </div>

          <button
            type="submit"
            disabled={isLoading}
            className="w-full rounded-lg bg-stone-700 py-3 font-medium text-white shadow-md transition hover:bg-stone-800 disabled:opacity-50"
          >
            {isLoading ? t.auth.registering : t.auth.registerButton}
          </button>
        </form>

        <div className="my-6 flex items-center gap-3">
          <div className="h-px flex-1 bg-stone-200" />
          <span className="text-xs text-stone-400">{t.auth.loginDivider}</span>
          <div className="h-px flex-1 bg-stone-200" />
        </div>

        <button
          type="button"
          onClick={() => void loginWithWeChat()}
          disabled={isWeChatLoading}
          className="flex w-full items-center justify-center gap-2 rounded-lg border border-stone-300 bg-[#fffaf4] py-3 font-medium text-stone-700 shadow-sm transition hover:border-stone-400 hover:bg-[#efe6d8] hover:text-stone-800 disabled:bg-[#fffaf4] disabled:text-stone-500 disabled:opacity-100"
        >
          <MessageCircle className="h-4 w-4" aria-hidden="true" />
          {t.auth.registerWithWeChat}
        </button>

        <div className="mt-6 text-center">
          <button
            type="button"
            onClick={() => router.push('/login')}
            className="text-stone-500 transition hover:text-stone-700"
          >
            {t.auth.backToLogin}
          </button>
        </div>
    </div>
  )
}
