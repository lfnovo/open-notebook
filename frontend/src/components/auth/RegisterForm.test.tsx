import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { RegisterForm } from './RegisterForm'

vi.mock('@/lib/config', () => ({
  getApiUrl: vi.fn().mockResolvedValue('http://127.0.0.1:5055'),
}))

vi.mock('@/lib/stores/auth-store', () => ({
  useAuthStore: () => ({
    checkAuthRequired: vi.fn(),
  }),
}))

describe('RegisterForm', () => {
  it('renders as an embedded auth panel instead of a standalone full-screen page', () => {
    const { container } = render(<RegisterForm />)

    expect(screen.getByRole('heading', { name: 'Create Account' })).toBeInTheDocument()
    expect(screen.getByPlaceholderText('Email address')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Send Code' })).toBeInTheDocument()

    const panel = container.firstElementChild as HTMLElement
    expect(panel.className).not.toContain('min-h-screen')
    expect(panel.className).toContain('max-w-md')
  })
})
