import { LoginForm } from '@/components/auth/LoginForm'
import { ErrorBoundary } from '@/components/common/ErrorBoundary'

export default function LoginPage() {
  return (
    <ErrorBoundary>
      <LoginForm />
    </ErrorBoundary>
  )
}