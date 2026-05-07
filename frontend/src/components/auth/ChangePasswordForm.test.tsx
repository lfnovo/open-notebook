import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, it, expect, vi } from 'vitest'
import { ChangePasswordForm } from './ChangePasswordForm'

const mutateAsyncMock = vi.hoisted(() => vi.fn())
const changePasswordState = vi.hoisted(() => ({
  isPending: false,
  error: null as unknown,
}))

vi.mock('@/lib/hooks/use-toast', () => ({
  useToast: () => ({ toast: vi.fn() }),
}))

vi.mock('@/lib/hooks/use-change-password', () => ({
  useChangePassword: () => ({
    mutateAsync: mutateAsyncMock,
    isPending: changePasswordState.isPending,
    error: changePasswordState.error,
  }),
}))

describe('ChangePasswordForm', () => {
  beforeEach(() => {
    mutateAsyncMock.mockReset()
    changePasswordState.isPending = false
    changePasswordState.error = null
  })

  it('renders current/new/confirm password fields and submit button', () => {
    render(<ChangePasswordForm />)

    expect(screen.getByPlaceholderText('Current Password')).toBeInTheDocument()
    expect(screen.getByPlaceholderText('New Password')).toBeInTheDocument()
    expect(screen.getByPlaceholderText('Confirm New Password')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Change Password' })).toBeInTheDocument()
  })

  it('shows the backend password error instead of a transport error', async () => {
    mutateAsyncMock.mockRejectedValueOnce({
      response: { data: { detail: 'Current password is incorrect' } },
      message: 'Request failed with status code 400',
    })

    render(<ChangePasswordForm />)

    fireEvent.change(screen.getByPlaceholderText('Current Password'), {
      target: { value: 'wrong-password' },
    })
    fireEvent.change(screen.getByPlaceholderText('New Password'), {
      target: { value: 'NewPass1' },
    })
    fireEvent.change(screen.getByPlaceholderText('Confirm New Password'), {
      target: { value: 'NewPass1' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Change Password' }))

    await waitFor(() => expect(mutateAsyncMock).toHaveBeenCalledTimes(1))
    expect(await screen.findByText('Current password is incorrect.')).toBeInTheDocument()
    expect(screen.queryByText('Request failed with status code 400')).not.toBeInTheDocument()
  })
})
