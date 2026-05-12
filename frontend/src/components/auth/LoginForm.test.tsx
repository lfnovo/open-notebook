import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { LoginForm } from './LoginForm'

const mockLoginWithWeChat = vi.fn()
let mockAuthState = {
  isLoading: false,
  isPasswordLoading: false,
  isWeChatLoading: false,
  error: null as string | null,
}

vi.mock('@/lib/config', () => ({
  getConfig: vi.fn().mockResolvedValue({
    apiUrl: 'http://127.0.0.1:5055',
    version: 'test-version',
    buildTime: '2026-04-23T00:00:00.000Z',
  }),
}))

vi.mock('@/lib/hooks/use-auth', () => ({
  useAuth: () => ({
    login: vi.fn(),
    loginWithWeChat: mockLoginWithWeChat,
    isLoading: mockAuthState.isLoading,
    isPasswordLoading: mockAuthState.isPasswordLoading,
    isWeChatLoading: mockAuthState.isWeChatLoading,
    error: mockAuthState.error,
  }),
}))

vi.mock('@/lib/stores/auth-store', () => ({
  useAuthStore: () => ({
    authRequired: true,
    checkAuthRequired: vi.fn(),
    hasHydrated: true,
    isAuthenticated: false,
  }),
}))

describe('LoginForm', () => {
  beforeEach(() => {
    mockLoginWithWeChat.mockReset()
    mockAuthState = {
      isLoading: false,
      isPasswordLoading: false,
      isWeChatLoading: false,
      error: null,
    }
  })

  it('renders as an embedded auth panel instead of owning a standalone full-screen page', async () => {
    const { container } = render(<LoginForm />)

    const usernameInput = await screen.findByPlaceholderText('Username / Email / Researcher ID')
    const passwordInput = screen.getByPlaceholderText('Password')
    expect(screen.getByText('Remember me')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Forgot password?' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Register new account' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Show password' })).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Lumina' })).not.toBeInTheDocument()
    expect(screen.queryByText('Illuminating Discovery, Advancing Life.')).not.toBeInTheDocument()

    const panel = container.firstElementChild as HTMLElement
    expect(panel.className).not.toContain('min-h-screen')
    expect(panel.className).toContain('max-w-[560px]')
    expect(panel.getAttribute('style') || '').not.toContain('loginpage-bg')

    const framelessPanel = Array.from(panel.querySelectorAll('div')).find((element) =>
      (element as HTMLElement).className.includes('px-7 py-7')
    ) as HTMLElement | undefined
    expect(framelessPanel).toBeDefined()
    expect(framelessPanel?.className).not.toContain('border ')
    expect(framelessPanel?.className).not.toContain('shadow-')
    expect(framelessPanel?.className).not.toContain('rounded-')

    const form = screen.getByRole('form', { name: 'Login form' })
    const submitButton = screen.getByRole('button', { name: 'Sign In' })
    expect(form.className).toContain('space-y-5')
    expect(form.className).not.toContain('font-fangsong')
    expect(submitButton.className).toContain('h-11')
    expect(submitButton.className).toContain('text-base')
    expect(submitButton.className).toContain('rounded-none')

    const usernameWrapper = usernameInput.parentElement as HTMLElement
    const passwordWrapper = passwordInput.parentElement as HTMLElement
    expect(usernameInput.className).toContain('text-base')
    expect(passwordInput.className).toContain('text-base')
    expect(usernameWrapper.className).toContain('rounded-none')
    expect(passwordWrapper.className).toContain('rounded-none')
    expect(usernameWrapper.className).toContain('border')
    expect(passwordWrapper.className).toContain('border')
    expect(usernameWrapper.className).toContain('border-2')
    expect(passwordWrapper.className).toContain('border-2')
    expect(usernameWrapper.className).toContain('border-black/35')
    expect(passwordWrapper.className).toContain('border-black/35')
  })

  it('offers WeChat scan login as the first-stage platform entry', async () => {
    render(<LoginForm />)

    expect(await screen.findByRole('button', { name: 'Sign in with WeChat' })).toBeInTheDocument()
  })

  it('keeps the WeChat scan login button opaque across hover and disabled states', async () => {
    render(<LoginForm />)

    const wechatButton = await screen.findByRole('button', { name: 'Sign in with WeChat' })

    expect(wechatButton.className).not.toContain('bg-[#fffaf4]/75')
    expect(wechatButton.className).toContain('bg-[#fffaf4]')
    expect(wechatButton.className).toContain('hover:bg-[#efe6d8]')
    expect(wechatButton.className).toContain('hover:text-stone-800')
    expect(wechatButton.className).toContain('hover:border-black/45')
    expect(wechatButton.className).toContain('disabled:opacity-100')
    expect(wechatButton.className).toContain('disabled:bg-[#fffaf4]')
    expect(wechatButton.className).toContain('disabled:text-stone-500')
  })

  it('does not show password login loading copy while WeChat login is pending', async () => {
    mockAuthState = {
      isLoading: true,
      isPasswordLoading: false,
      isWeChatLoading: true,
      error: null,
    }
    render(<LoginForm />)

    expect(await screen.findByRole('button', { name: 'Sign In' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Signing in...' })).not.toBeInTheDocument()
  })

  it('localizes the WeChat login not configured error from the backend', async () => {
    mockAuthState = {
      isLoading: false,
      isPasswordLoading: false,
      isWeChatLoading: false,
      error: 'WeChat web login is not configured',
    }

    render(<LoginForm />)

    expect(await screen.findByText('WeChat login is not configured. Please contact the administrator.')).toBeInTheDocument()
    expect(screen.queryByText('WeChat web login is not configured')).not.toBeInTheDocument()
  })
})
