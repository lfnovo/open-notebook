import { render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import DashboardLayout from './layout'

vi.mock('@/components/layout/AppShell', () => ({
  AppShell: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="app-shell">{children}</div>
  ),
}))

vi.mock('@/components/providers/ModalProvider', () => ({
  ModalProvider: () => null,
}))

vi.mock('@/components/common/CommandPalette', () => ({
  CommandPalette: () => null,
}))

vi.mock('@/lib/hooks/use-create-dialogs', () => ({
  CreateDialogsProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}))

describe('DashboardLayout', () => {
  it('renders authenticated dashboard pages inside the app shell sidebar layout', async () => {
    render(
      <DashboardLayout>
        <div>Dashboard content</div>
      </DashboardLayout>
    )

    await waitFor(() => {
      expect(screen.getByTestId('app-shell')).toBeInTheDocument()
    })
    expect(screen.getByText('Dashboard content')).toBeInTheDocument()
  })
})
