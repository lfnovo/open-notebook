import { SignupForm } from '@/components/auth/SignupForm'
import { ErrorBoundary } from '@/components/common/ErrorBoundary'

export default function SignupPage() {
  return (
    <ErrorBoundary>
      <SignupForm />
    </ErrorBoundary>
  )
}


