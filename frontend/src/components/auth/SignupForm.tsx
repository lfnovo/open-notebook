'use client'

import { useState } from 'react'
import Image from 'next/image'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

export function SignupForm() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')

  // UI-only form – no real submit logic yet
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    // In the future, add signup API call here
  }

  const isFormValid = email.trim() && password.trim() && confirmPassword.trim()

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
            <Button
              type="submit"
              className="w-full"
              disabled={!isFormValid}
            >
              Sign up 
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
