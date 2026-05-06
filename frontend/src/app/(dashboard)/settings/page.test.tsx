/* eslint-disable @typescript-eslint/no-explicit-any */
import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import SettingsPage from './page'
import { useSettings } from '@/lib/hooks/use-settings'
import { useUpdateWorkspaceSystemPolicy, useWorkspaceSystemPolicy } from '@/lib/hooks/use-workspaces'

vi.mock('@/lib/hooks/use-settings', () => ({
  useSettings: vi.fn(),
}))

vi.mock('@/lib/hooks/use-workspaces', () => ({
  useWorkspaceSystemPolicy: vi.fn(),
  useUpdateWorkspaceSystemPolicy: vi.fn(),
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
    vi.mocked(useWorkspaceSystemPolicy).mockReturnValue({
      data: {
        policy: {
          member_can_read: true,
          member_can_create_source: true,
          member_can_update_own_source: true,
          member_can_process_own_source: true,
          member_can_delete_own_source: false,
          member_can_remove_source: true,
          member_can_create_note: true,
          member_can_update_own_note: true,
          member_can_delete_own_note: false,
          member_can_delete_chat: false,
          member_can_update_notebook: false,
        },
      },
      isLoading: false,
    } as any)
    vi.mocked(useUpdateWorkspaceSystemPolicy).mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    } as any)
  })

  it('shows application settings without the password change form', () => {
    render(<SettingsPage />)

    expect(screen.getByText('Settings form')).toBeInTheDocument()
    expect(screen.getByText('Workspace system limits')).toBeInTheDocument()
    expect(screen.queryByText('Change password form')).not.toBeInTheDocument()
  })
})
