import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { RegisterForm } from './RegisterForm'

const mockLoginWithWeChat = vi.fn()
let mockAuthState = {
  isWeChatLoading: false,
  error: null as string | null,
}

vi.mock('@/lib/config', () => ({
  getApiUrl: vi.fn().mockResolvedValue('http://127.0.0.1:5055'),
}))

vi.mock('@/lib/hooks/use-auth', () => ({
  useAuth: () => ({
    loginWithWeChat: mockLoginWithWeChat,
    isWeChatLoading: mockAuthState.isWeChatLoading,
    error: mockAuthState.error,
  }),
}))

vi.mock('@/lib/stores/auth-store', () => ({
  useAuthStore: () => ({
    checkAuthRequired: vi.fn(),
  }),
}))

describe('RegisterForm', () => {
  beforeEach(() => {
    mockLoginWithWeChat.mockReset()
    mockAuthState = {
      isWeChatLoading: false,
      error: null,
    }
  })

  it('renders as an embedded auth panel instead of a standalone full-screen page', () => {
    const { container } = render(<RegisterForm />)

    expect(screen.getByRole('heading', { name: 'Create Account' })).toBeInTheDocument()
    expect(screen.getByPlaceholderText('Email address')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Send Code' })).toBeInTheDocument()

    const panel = container.firstElementChild as HTMLElement
    expect(panel.className).not.toContain('min-h-screen')
    expect(panel.className).toContain('max-w-md')
  })

  it('offers WeChat scan registration through the shared OAuth flow', () => {
    render(<RegisterForm />)

    const wechatButton = screen.getByRole('button', { name: 'Sign up or sign in with WeChat' })
    expect(wechatButton).toBeInTheDocument()

    fireEvent.click(wechatButton)

    expect(mockLoginWithWeChat).toHaveBeenCalledOnce()
  })

  it('localizes the WeChat not configured error on the registration page', () => {
    mockAuthState = {
      isWeChatLoading: false,
      error: 'WeChat web login is not configured',
    }

    render(<RegisterForm />)

    expect(screen.getByText('WeChat login is not configured. Please contact the administrator.')).toBeInTheDocument()
    expect(screen.queryByText('WeChat web login is not configured')).not.toBeInTheDocument()
  })
})
