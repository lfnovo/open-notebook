import { render, screen, within } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import RegisterPage from './page'

vi.mock('@/components/auth/RegisterForm', () => ({
  RegisterForm: () => <form aria-label="Register form" />,
}))

describe('RegisterPage', () => {
  it('places the register form inside the shared guest page flow', () => {
    render(<RegisterPage />)

    const banner = screen.getByRole('banner')
    const primaryNav = within(banner).getByRole('navigation', { name: '主导航' })
    const accountNav = within(banner).getByRole('navigation', { name: '账户操作' })

    expect(within(primaryNav).getByRole('link', { name: '公开内容' })).toHaveAttribute('href', '/public')
    expect(within(accountNav).getByRole('link', { name: '登录' })).toHaveAttribute('href', '/login')
    expect(within(accountNav).getByRole('link', { name: '注册' })).toHaveAttribute('href', '/register')
    expect(screen.getByRole('form', { name: 'Register form' })).toBeInTheDocument()
  })
})
