'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Image from 'next/image'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { useAuthStore } from '@/lib/stores/auth-store'
import { AlertCircle } from 'lucide-react'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'

export function SignupForm() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const { signup, isLoading, error } = useAuthStore()
  const router = useRouter()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    // Validate passwords match
    if (password !== confirmPassword) {
      return
    }

    // Validate password length
    if (password.length < 8) {
      return
    }

    const success = await signup(email, password, confirmPassword)
    if (success) {
      // Redirect to login page after successful signup
      router.push('/login?signup=success')
    }
  }

  const isFormValid = email.trim() && password.trim() && confirmPassword.trim() && password === confirmPassword && password.length >= 8

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <CardTitle>Create an account</CardTitle>
          <CardDescription>
            Sign up with your email or continue with a provider
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Input
                type="email"
                placeholder="Email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                autoComplete="email"
              />
            </div>
            <div className="space-y-2">
              <Input
                type="password"
                placeholder="Password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="new-password"
              />
            </div>
            <div className="space-y-2">
              <Input
                type="password"
                placeholder="Confirm password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                autoComplete="new-password"
              />
            </div>
            {error && (
              <div className="flex items-start gap-2 text-red-600 text-sm">
                <AlertCircle className="h-4 w-4 mt-0.5 flex-shrink-0" />
                <div className="flex-1">{error}</div>
              </div>
            )}
            
            {password && confirmPassword && password !== confirmPassword && (
              <div className="flex items-start gap-2 text-red-600 text-sm">
                <AlertCircle className="h-4 w-4 mt-0.5 flex-shrink-0" />
                <div className="flex-1">Passwords do not match</div>
              </div>
            )}

            {password && password.length > 0 && password.length < 8 && (
              <div className="flex items-start gap-2 text-red-600 text-sm">
                <AlertCircle className="h-4 w-4 mt-0.5 flex-shrink-0" />
                <div className="flex-1">Password must be at least 8 characters long</div>
              </div>
            )}

            <Button
              type="submit"
              className="w-full"
              disabled={!isFormValid || isLoading}
            >
              {isLoading ? (
                <span className="flex items-center gap-2">
                  <LoadingSpinner size="sm" />
                  Creating account...
                </span>
              ) : (
                'Sign up'
              )}
            </Button>
          </form>

          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <div className="h-px flex-1 bg-border" />
            <span>or</span>
            <div className="h-px flex-1 bg-border" />
          </div>

          <div className="grid gap-2">
            <Button variant="outline" type="button" className="w-full justify-center">
              <span className="flex items-center gap-2">
                <Image
                  src="/Google_logo.webp"
                  alt="Google"
                  width={20}
                  height={20}
                />
                <span>Continue with Google</span>
              </span>
            </Button>
            <Button variant="outline" type="button" className="w-full justify-center">
              <span className="flex items-center gap-2">
                <Image
                  src="/apple_logo.svg"
                  alt="Apple"
                  width={20}
                  height={20}
                />
                <span>Continue with Apple</span>
              </span>
            </Button>
            <Button variant="outline" type="button" className="w-full justify-center">
              <span className="flex items-center gap-2">
                <Image
                  src="/Microsoft_logo.svg"
                  alt="Microsoft"
                  width={40}
                  height={40}
                />
                <span>Continue with Microsoft</span>
              </span>
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
