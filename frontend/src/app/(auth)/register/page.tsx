import { RegisterForm } from '@/components/auth/RegisterForm'
import { AuthPageShell } from '@/components/auth/AuthPageShell'

export default function RegisterPage() {
  return (
    <AuthPageShell
      title="创建 Lumina 账号"
      description="注册后即可保存研究资料、组织团队协作，并将合适的内容公开分享给全网只读访问。"
    >
      <RegisterForm />
    </AuthPageShell>
  )
}
