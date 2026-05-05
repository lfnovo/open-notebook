/* eslint-disable @typescript-eslint/no-explicit-any */
import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import SettingsPage from './page'
import { useSettings } from '@/lib/hooks/use-settings'

vi.mock('@/lib/hooks/use-settings', () => ({
  useSettings: vi.fn(),
}))

vi.mock('./components/SettingsForm', () => ({
  SettingsForm: () => <div>Settings form</div>,
}))

vi.mock('@/components/auth/ChangePasswordForm', () => ({
  ChangePasswordForm: () => <div>Change password form</div>,
}))

describe('SettingsPage', () => {
  beforeEach(() => {
    vi.mocked(useSettings).mockReturnValue({
      refetch: vi.fn(),
    } as any)
  })

  it('shows application settings without the password change form', () => {
    render(<SettingsPage />)

    expect(screen.getByText('Settings form')).toBeInTheDocument()
    expect(screen.queryByText('Change password form')).not.toBeInTheDocument()
  })
})
