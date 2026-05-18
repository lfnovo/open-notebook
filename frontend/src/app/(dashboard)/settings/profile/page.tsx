'use client'

import { FormEvent, useEffect, useState } from 'react'
import { Loader2, LogOut, UserCircle } from 'lucide-react'
import { useRouter } from 'next/navigation'
import { ChangePasswordForm } from '@/components/auth/ChangePasswordForm'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { useAuth } from '@/lib/hooks/use-auth'
import { useCompleteProfile, useProfile, useUpdateProfile } from '@/lib/hooks/use-profile'
import { useTranslation } from '@/lib/hooks/use-translation'
import { languages } from '@/lib/locales'
import { getApiUrl } from '@/lib/config'

const THEME_VALUES = ['system', 'light', 'dark'] as const

export default function ProfilePage() {
  const { t } = useTranslation()
  const router = useRouter()
  const { logout } = useAuth()
  const { data: profile, isLoading, error } = useProfile()
  const updateProfile = useUpdateProfile()
  const completeProfile = useCompleteProfile()
  const [displayName, setDisplayName] = useState('')
  const [email, setEmail] = useState('')
  const [verificationCode, setVerificationCode] = useState('')
  const [locale, setLocale] = useState<string | null>(null)
  const [theme, setTheme] = useState<string | null>(null)
  const [isSendingCode, setIsSendingCode] = useState(false)
  const [codeError, setCodeError] = useState<string | null>(null)
  const needsEmailCompletion = profile?.login_provider === 'wechat' && !profile.email

  useEffect(() => {
    if (!profile) return
    setDisplayName(profile.display_name || '')
    setEmail(profile.email || '')
    setLocale(profile.locale || 'system')
    setTheme(profile.theme || 'system')
  }, [profile])

  const sendVerificationCode = async () => {
    if (!email.trim() || isSendingCode) return
    setIsSendingCode(true)
    setCodeError(null)
    try {
      const selectedLocale = locale ?? profile?.locale ?? 'system'
      const apiUrl = await getApiUrl()
      const response = await fetch(`${apiUrl}/api/auth/send-code`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: email.trim(),
          purpose: 'profile_email',
          language: selectedLocale === 'zh-CN' ? 'zh-CN' : 'en',
        }),
      })
      const data = await response.json().catch(() => null)
      if (!response.ok || !data?.success) {
        setCodeError(data?.message || t.common.error)
      }
    } catch {
      setCodeError(t.common.error)
    } finally {
      setIsSendingCode(false)
    }
  }

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault()
    if (!profile || updateProfile.isPending || completeProfile.isPending) return

    if (needsEmailCompletion) {
      completeProfile.mutate(
        {
          email: email.trim(),
          verification_code: verificationCode.trim(),
        },
        {
          onSuccess: () => router.push('/notebooks'),
        },
      )
      return
    }

    const selectedLocale = locale ?? profile.locale ?? 'system'
    const selectedTheme = theme ?? profile.theme ?? 'system'

    updateProfile.mutate({
      display_name: displayName.trim() || null,
      locale: selectedLocale === 'system' ? null : selectedLocale,
      theme: selectedTheme === 'system' ? null : selectedTheme,
    })
  }

  return (
          <div className="flex-1 overflow-y-auto">
        <div className="mx-auto flex w-full max-w-4xl flex-col gap-6 p-6">
          <div className="flex items-center gap-3">
            <UserCircle className="h-6 w-6 text-muted-foreground" />
            <div>
              <h1 className="text-2xl font-semibold tracking-normal">{t.profile.title}</h1>
              <p className="text-sm text-muted-foreground">{t.profile.description}</p>
            </div>
          </div>

          {isLoading ? (
            <div className="flex min-h-64 items-center justify-center">
              <LoadingSpinner />
            </div>
          ) : error || !profile ? (
            <div className="rounded-md border border-destructive/30 bg-destructive/5 p-4 text-sm text-destructive">
              {t.profile.loadFailed}
            </div>
          ) : (
            <>
              <form onSubmit={handleSubmit} className="rounded-md border p-5">
                {needsEmailCompletion && (
                  <div className="mb-5 rounded-md border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
                    <p className="font-medium">{t.profile.completeTitle}</p>
                    <p className="mt-1 text-amber-800">{t.profile.completeDescription}</p>
                  </div>
                )}
                <div className="grid gap-5 md:grid-cols-2">
                  <div className="space-y-2">
                    <Label htmlFor="profile-username">{t.profile.username}</Label>
                    <Input id="profile-username" value={profile.username} disabled />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="profile-email">{t.profile.email}</Label>
                    {needsEmailCompletion ? (
                      <div className="flex gap-2">
                        <Input
                          id="profile-email"
                          type="email"
                          value={email}
                          onChange={(event) => setEmail(event.target.value)}
                          autoComplete="email"
                        />
                        <Button
                          type="button"
                          variant="outline"
                          onClick={() => void sendVerificationCode()}
                          disabled={isSendingCode || !email.trim()}
                        >
                          {isSendingCode ? t.profile.sendingCode : t.profile.sendCode}
                        </Button>
                      </div>
                    ) : (
                      <Input id="profile-email" value={profile.email || t.common.unknown} disabled />
                    )}
                    {codeError && <p className="text-xs text-destructive">{codeError}</p>}
                  </div>
                  {needsEmailCompletion && (
                    <div className="space-y-2">
                      <Label htmlFor="profile-verification-code">
                        {t.profile.verificationCode}
                      </Label>
                      <Input
                        id="profile-verification-code"
                        value={verificationCode}
                        onChange={(event) => setVerificationCode(event.target.value)}
                        inputMode="numeric"
                        autoComplete="one-time-code"
                      />
                    </div>
                  )}
                  <div className="space-y-2">
                    <Label htmlFor="display-name">{t.profile.displayName}</Label>
                    <Input
                      id="display-name"
                      value={displayName}
                      onChange={(event) => setDisplayName(event.target.value)}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>{t.profile.role}</Label>
                    <div className="flex h-10 items-center">
                      <Badge variant={profile.role === 'admin' ? 'secondary' : 'outline'}>
                        {profile.role === 'admin' ? t.users.roleAdmin : t.users.roleUser}
                      </Badge>
                    </div>
                  </div>
                  <div className="space-y-2">
                    <Label>{t.profile.status}</Label>
                    <div className="flex h-10 items-center">
                      <Badge variant={profile.status === 'active' ? 'outline' : 'secondary'}>
                        {profile.status === 'active' ? t.users.statusActive : t.users.statusDisabled}
                      </Badge>
                    </div>
                  </div>
                  <div className="space-y-2">
                    <Label>{t.profile.lastLogin}</Label>
                    <Input value={profile.last_login_at || t.common.unknown} disabled />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="profile-language">{t.profile.language}</Label>
                    <Select value={locale ?? profile.locale ?? 'system'} onValueChange={setLocale}>
                      <SelectTrigger id="profile-language" className="w-full">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="system">{t.profile.systemDefault}</SelectItem>
                        {languages.map((language) => (
                          <SelectItem key={language.code} value={language.code}>
                            {language.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="profile-theme">{t.profile.theme}</Label>
                    <Select value={theme ?? profile.theme ?? 'system'} onValueChange={setTheme}>
                      <SelectTrigger id="profile-theme" className="w-full">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {THEME_VALUES.map((value) => (
                          <SelectItem key={value} value={value}>
                            {themeLabel(value, t)}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                </div>
                <div className="mt-5 flex flex-col gap-2 sm:flex-row sm:justify-end">
                  <Button type="button" variant="destructive" onClick={logout}>
                    <LogOut className="h-4 w-4" />
                    {t.common.signOut}
                  </Button>
                  <Button
                    type="submit"
                    disabled={
                      updateProfile.isPending
                      || completeProfile.isPending
                      || (needsEmailCompletion && (!email.trim() || !verificationCode.trim()))
                    }
                  >
                    {(updateProfile.isPending || completeProfile.isPending) && (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    )}
                    {t.common.save}
                  </Button>
                </div>
              </form>

              {!needsEmailCompletion && <ChangePasswordForm />}
            </>
          )}
        </div>
      </div>
  )
}

function themeLabel(value: string, t: ReturnType<typeof useTranslation>['t']) {
  if (value === 'light') return t.profile.themeLight
  if (value === 'dark') return t.profile.themeDark
  return t.profile.systemDefault
}
