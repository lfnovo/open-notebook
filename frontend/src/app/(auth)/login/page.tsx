import { LoginForm } from '@/components/auth/LoginForm'
import { AuthPageShell } from '@/components/auth/AuthPageShell'

export default function LoginPage() {
  return (
    <AuthPageShell
      title="欢迎回来"
      description="登录后继续管理你的笔记本、来源和团队共享内容，也可以先浏览全网公开内容。"
    >
      <LoginForm />
    </AuthPageShell>
  )
}
