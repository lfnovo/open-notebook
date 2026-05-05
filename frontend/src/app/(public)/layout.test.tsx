import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import PublicLayout from './layout'

vi.mock('@/components/layout/AppShell', () => ({
  AppShell: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="app-shell">{children}</div>
  ),
}))

vi.mock('@/components/providers/ModalProvider', () => ({
  ModalProvider: () => null,
}))

vi.mock('@/lib/hooks/use-create-dialogs', () => ({
  CreateDialogsProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}))

describe('PublicLayout', () => {
  it('renders public pages without the authenticated app shell', () => {
    render(
      <PublicLayout>
        <div>Public content</div>
      </PublicLayout>
    )

    expect(screen.getByText('Public content')).toBeInTheDocument()
    expect(screen.queryByTestId('app-shell')).not.toBeInTheDocument()
  })
})
