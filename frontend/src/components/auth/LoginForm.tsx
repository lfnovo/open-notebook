'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { AlertCircle, Eye, EyeOff, Lock, MessageCircle, User } from 'lucide-react'
import { useAuth } from '@/lib/hooks/use-auth'
import { useAuthStore } from '@/lib/stores/auth-store'
import { getConfig } from '@/lib/config'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Checkbox } from '@/components/ui/checkbox'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import { useTranslation } from '@/lib/hooks/use-translation'

export function LoginForm() {
  const { t, language } = useTranslation()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [rememberMe, setRememberMe] = useState(true)
  const { login, loginWithWeChat, isPasswordLoading, isWeChatLoading, error } = useAuth()
  const { authRequired, checkAuthRequired, hasHydrated, isAuthenticated } = useAuthStore()
  const [isCheckingAuth, setIsCheckingAuth] = useState(true)
  const [configInfo, setConfigInfo] = useState<{ apiUrl: string; version: string; buildTime: string } | null>(null)
  const router = useRouter()
  const displayedError =
    error === 'WeChat web login is not configured'
      ? t.auth.weChatNotConfigured
      : error

  useEffect(() => {
    getConfig().then(cfg => {
      setConfigInfo({
        apiUrl: cfg.apiUrl,
        version: cfg.version,
        buildTime: cfg.buildTime,
      })
    }).catch(err => {
      console.error('Failed to load config:', err)
    })
  }, [])

  useEffect(() => {
    if (!hasHydrated) {
      return
    }

    const checkAuth = async () => {
      try {
        const required = await checkAuthRequired()

        if (!required) {
          router.push('/notebooks')
        }
      } catch (error) {
        console.error('Error checking auth requirement:', error)
      } finally {
        setIsCheckingAuth(false)
      }
    }

    if (authRequired !== null) {
      if (!authRequired && isAuthenticated) {
        router.push('/notebooks')
      } else {
        setIsCheckingAuth(false)
      }
    } else {
      void checkAuth()
    }
  }, [hasHydrated, authRequired, checkAuthRequired, router, isAuthenticated])

  if (!hasHydrated || isCheckingAuth) {
    return (
      <div className="flex w-full max-w-[560px] items-center justify-center rounded-xl border border-stone-200 bg-white/80 p-10 shadow-sm">
        <LoadingSpinner />
      </div>
    )
  }

  if (authRequired === null) {
    return (
      <Card className="w-full max-w-md border-stone-300/80 bg-[#f7f0e5]/90 shadow-xl shadow-stone-400/10">
        <CardHeader className="text-center">
          <CardTitle>{t.common.connectionError}</CardTitle>
          <CardDescription>
            {t.common.unableToConnect}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="flex items-start gap-2 text-red-700 text-sm">
              <AlertCircle className="h-4 w-4 mt-0.5 flex-shrink-0" />
              <div className="flex-1">
                {displayedError || t.auth.connectErrorHint}
              </div>
            </div>

            {configInfo && (
              <div className="space-y-2 text-xs text-stone-600 border-t border-stone-300/80 pt-3">
                <div className="font-medium">{t.common.diagnosticInfo}:</div>
                <div className="space-y-1 font-mono">
                  <div>{t.common.version}: {configInfo.version}</div>
                  <div>{t.common.built}: {new Date(configInfo.buildTime).toLocaleString(language === 'zh-CN' ? 'zh-CN' : language === 'zh-TW' ? 'zh-TW' : 'en-US')}</div>
                  <div className="break-all">{t.common.apiUrl}: {configInfo.apiUrl}</div>
                  <div className="break-all">{t.common.frontendUrl}: {typeof window !== 'undefined' ? window.location.href : 'N/A'}</div>
                </div>
                <div className="text-xs pt-2">
                  {t.common.checkConsoleLogs}
                </div>
              </div>
            )}

            <Button
              onClick={() => window.location.reload()}
              className="w-full bg-slate-600 hover:bg-slate-700"
            >
              {t.common.retryConnection}
            </Button>
          </div>
        </CardContent>
      </Card>
    )
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (username.trim() && password.trim()) {
      try {
        await login(username, password)
      } catch (error) {
        console.error('Unhandled error during login:', error)
      }
    }
  }

  return (
    <div className="w-full max-w-[560px] text-stone-700">
        <div className="px-7 py-7 sm:px-8 sm:py-8">
          <form onSubmit={handleSubmit} className="space-y-5 text-left" aria-label="Login form">
              <label className="sr-only" htmlFor="login-username">{t.auth.usernamePlaceholder}</label>
              <div className="flex h-12 items-center rounded-none border-2 border-black/35 bg-[#fffaf4]/92 px-4 shadow-[0_6px_18px_rgba(84,64,43,0.03)] transition focus-within:border-black/50 focus-within:bg-[#fffaf4] focus-within:shadow-[0_0_0_2px_rgba(60,60,60,0.10)]">
                <User className="mr-3 h-5 w-5 flex-shrink-0 text-stone-500" />
                <Input
                  id="login-username"
                  type="text"
                  placeholder={t.auth.loginIdentifierPlaceholder}
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  disabled={isPasswordLoading}
                  autoComplete="username"
                  className="h-auto border-0 bg-transparent px-0 py-0 text-base text-stone-700 shadow-none placeholder:text-base placeholder:text-stone-400 focus-visible:ring-0"
                />
              </div>

              <label className="sr-only" htmlFor="login-password">{t.auth.passwordPlaceholder}</label>
              <div className="flex h-12 items-center rounded-none border-2 border-black/35 bg-[#fffaf4]/92 px-4 shadow-[0_6px_18px_rgba(84,64,43,0.03)] transition focus-within:border-black/50 focus-within:bg-[#fffaf4] focus-within:shadow-[0_0_0_2px_rgba(60,60,60,0.10)]">
                <Lock className="mr-3 h-5 w-5 flex-shrink-0 text-stone-500" />
                <Input
                  id="login-password"
                  type={showPassword ? 'text' : 'password'}
                  placeholder={t.auth.passwordPlaceholder}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  disabled={isPasswordLoading}
                  autoComplete="current-password"
                  className="h-auto border-0 bg-transparent px-0 py-0 text-base text-stone-700 shadow-none placeholder:text-base placeholder:text-stone-400 focus-visible:ring-0"
                />
                <button
                  type="button"
                  aria-label={showPassword ? t.auth.hidePassword : t.auth.showPassword}
                  className="ml-2 inline-flex h-9 w-9 items-center justify-center rounded-full text-stone-500 transition hover:bg-stone-200/40 hover:text-stone-700"
                  onClick={() => setShowPassword((value) => !value)}
                >
                  {showPassword ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
                </button>
              </div>

              <div className="flex items-center justify-between gap-4 pt-1 text-sm text-stone-600">
                <label className="flex items-center gap-2">
                  <Checkbox
                    checked={rememberMe}
                    onCheckedChange={(checked) => setRememberMe(checked === true)}
                    className="size-4 border-stone-400/70 bg-[#fffaf4]/85 data-[state=checked]:border-[#74685a] data-[state=checked]:bg-[#74685a]"
                  />
                  <span>{t.auth.rememberMe}</span>
                </label>
                <button
                  type="button"
                  className="transition hover:text-stone-800"
                  onClick={() => router.push('/forgot-password')}
                >
                  {t.auth.forgotPassword}
                </button>
              </div>

              {displayedError && (
                <div className="flex items-center gap-2 rounded-xl border border-red-200/80 bg-red-50/75 px-4 py-3 text-sm text-red-700">
                  <AlertCircle className="h-4 w-4 flex-shrink-0" />
                  {displayedError}
                </div>
              )}

              <Button
                type="submit"
                className="h-11 w-full rounded-none bg-[#6f6559] text-base font-medium tracking-normal text-white shadow-[0_16px_36px_rgba(111,101,89,0.20)] hover:bg-[#645a4e]"
                disabled={isPasswordLoading || !username.trim() || !password.trim()}
              >
                {isPasswordLoading ? t.auth.signingIn : t.auth.signIn}
              </Button>

              <div className="pt-1 text-center text-sm text-stone-500">
                {t.auth.loginDivider}
              </div>

              <Button
                type="button"
                className="h-11 w-full rounded-none border-2 border-black/30 bg-[#fffaf4] text-base font-medium tracking-normal text-stone-700 shadow-[0_10px_24px_rgba(84,64,43,0.08)] hover:border-black/45 hover:bg-[#efe6d8] hover:text-stone-800 disabled:bg-[#fffaf4] disabled:text-stone-500 disabled:opacity-100"
                disabled={isWeChatLoading}
                onClick={() => void loginWithWeChat()}
              >
                <MessageCircle className="h-5 w-5 text-[#1AAD19]" />
                {t.auth.signInWithWeChat}
              </Button>

              <div className="text-center">
                <button
                  type="button"
                  className="text-sm text-stone-600 transition hover:text-stone-800"
                  onClick={() => router.push('/register')}
                >
                  {t.auth.registerNewAccount}
                </button>
              </div>
          </form>
        </div>

        {configInfo && (
          <div className="pt-3 text-center text-[10px] text-stone-600/45">
            <div>{t.common.version} {configInfo.version}</div>
            <div className="font-mono text-[9px] break-all">{configInfo.apiUrl}</div>
          </div>
        )}
    </div>
  )
}
