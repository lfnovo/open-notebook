'use client'

import { useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Button } from '@/components/ui/button'
import { AlertCircle } from 'lucide-react'
import { useTranslation } from '@/lib/hooks/use-translation'
import { useChangePassword } from '@/lib/hooks/use-change-password'
import { getApiErrorMessage } from '@/lib/utils/error-handler'

export function ChangePasswordForm() {
  const { t } = useTranslation()
  const changePassword = useChangePassword()
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [localError, setLocalError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLocalError(null)

    if (!currentPassword.trim() || !newPassword.trim() || !confirmPassword.trim()) {
      setLocalError(t.auth.changePasswordFillAllFields)
      return
    }

    if (newPassword !== confirmPassword) {
      setLocalError(t.auth.changePasswordMismatch)
      return
    }

    if (newPassword.length < 4) {
      setLocalError(t.auth.changePasswordTooShort)
      return
    }

    let result
    try {
      result = await changePassword.mutateAsync({
        old_password: currentPassword,
        new_password: newPassword,
      })
    } catch (error) {
      setLocalError(getApiErrorMessage(error, t, 'auth.changePasswordError'))
      return
    }

    if (result?.success) {
      setCurrentPassword('')
      setNewPassword('')
      setConfirmPassword('')
    }
  }

  const errorMessage = localError || (changePassword.error instanceof Error ? changePassword.error.message : null)

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t.auth.changePasswordTitle}</CardTitle>
        <CardDescription>{t.auth.changePasswordDesc}</CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="current-password">{t.auth.currentPasswordLabel}</Label>
            <Input
              id="current-password"
              type="password"
              placeholder={t.auth.currentPasswordPlaceholder}
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
              autoComplete="current-password"
              disabled={changePassword.isPending}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="new-password">{t.auth.newPasswordLabel}</Label>
            <Input
              id="new-password"
              type="password"
              placeholder={t.auth.newPasswordPlaceholder}
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              autoComplete="new-password"
              disabled={changePassword.isPending}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="confirm-new-password">{t.auth.confirmNewPasswordLabel}</Label>
            <Input
              id="confirm-new-password"
              type="password"
              placeholder={t.auth.confirmNewPasswordPlaceholder}
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              autoComplete="new-password"
              disabled={changePassword.isPending}
            />
          </div>

          {errorMessage && (
            <div className="flex items-center gap-2 text-red-600 text-sm">
              <AlertCircle className="h-4 w-4" />
              {errorMessage}
            </div>
          )}

          <div className="flex justify-end">
            <Button
              type="submit"
              disabled={changePassword.isPending || !currentPassword.trim() || !newPassword.trim() || !confirmPassword.trim()}
            >
              {changePassword.isPending ? t.common.saving : t.auth.changePasswordButton}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  )
}
