/* eslint-disable @typescript-eslint/no-explicit-any */
import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import ProfilePage from './page'
import { useAuth } from '@/lib/hooks/use-auth'
import { useProfile, useUpdateProfile } from '@/lib/hooks/use-profile'

vi.mock('@/lib/hooks/use-profile', () => ({
  useProfile: vi.fn(),
  useUpdateProfile: vi.fn(),
}))

vi.mock('@/components/auth/ChangePasswordForm', () => ({
  ChangePasswordForm: () => <div>Change password form</div>,
}))

describe('ProfilePage', () => {
  const logout = vi.fn()

  beforeEach(() => {
    logout.mockClear()
    vi.mocked(useAuth).mockReturnValue({
      login: vi.fn(),
      logout,
      isLoading: false,
      error: null,
      isAuthenticated: true,
      username: 'admin',
    } as any)
    vi.mocked(useProfile).mockReturnValue({
      data: {
        id: 'app_user:admin',
        username: 'admin',
        display_name: 'Admin User',
        email: 'admin@example.com',
        role: 'admin',
        status: 'active',
        last_login_at: '2026-05-05T00:00:00Z',
        locale: 'zh-CN',
        theme: 'dark',
      },
      isLoading: false,
      error: null,
    } as any)
    vi.mocked(useUpdateProfile).mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    } as any)
  })

  it('keeps account settings focused on identity and places sign out here', () => {
    render(<ProfilePage />)

    expect(screen.getByLabelText('Username')).toHaveValue('admin')
    expect(screen.getByRole('button', { name: 'Sign Out' })).toBeInTheDocument()
    expect(screen.queryByText('Language')).not.toBeInTheDocument()
    expect(screen.queryByText('Theme')).not.toBeInTheDocument()
  })

  it('signs out from the profile page', () => {
    render(<ProfilePage />)

    fireEvent.click(screen.getByRole('button', { name: 'Sign Out' }))

    expect(logout).toHaveBeenCalledOnce()
  })
})
