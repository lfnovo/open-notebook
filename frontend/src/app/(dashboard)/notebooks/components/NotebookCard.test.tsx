import { render, screen } from '@testing-library/react'
import type { MouseEventHandler, ReactNode } from 'react'
import { describe, expect, it, vi } from 'vitest'
import { NotebookResponse } from '@/lib/types/api'
import { NotebookCard } from './NotebookCard'

vi.mock('@/lib/hooks/use-notebooks', () => ({
  useUpdateNotebook: vi.fn(() => ({
    mutate: vi.fn(),
  })),
}))

vi.mock('@/lib/hooks/use-profile', () => ({
  useProfile: vi.fn(() => ({
    data: { id: 'app_user:current-user', username: 'current-user' },
  })),
}))

vi.mock('@/components/ui/dropdown-menu', () => ({
  DropdownMenu: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  DropdownMenuTrigger: ({ children }: { children: ReactNode }) => <>{children}</>,
  DropdownMenuContent: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  DropdownMenuItem: ({
    children,
    disabled,
    onClick,
    className,
  }: {
    children: ReactNode
    disabled?: boolean
    onClick?: MouseEventHandler<HTMLButtonElement>
    className?: string
  }) => (
    <button
      type="button"
      aria-disabled={disabled ? 'true' : undefined}
      disabled={disabled}
      onClick={onClick}
      className={className}
    >
      {children}
    </button>
  ),
}))

vi.mock('@/components/share/ShareDialog', () => ({
  ShareDialog: () => null,
}))

vi.mock('./NotebookDeleteDialog', () => ({
  NotebookDeleteDialog: () => null,
}))

const baseNotebook: NotebookResponse = {
  id: 'notebook:research',
  name: 'Research Notes',
  description: 'Notebook description',
  archived: false,
  created: '2026-05-05T00:00:00Z',
  updated: '2026-05-05T00:00:00Z',
  source_count: 2,
  note_count: 3,
  password: null,
  creator_name: null,
  creator_username: 'owner-login',
  owner_id: 'app_user:owner123',
  visibility: 'private',
}

describe('NotebookCard', () => {
  it('shows the creator login name from profile data', () => {
    render(<NotebookCard notebook={baseNotebook} />)

    expect(
      screen.getByText((_, element) =>
        element?.textContent === 'Created by: owner-login'
      )
    ).toBeInTheDocument()
  })

  it('disables delete when the current user is not the notebook owner', async () => {
    render(<NotebookCard notebook={baseNotebook} />)

    expect(screen.getByText('Delete').closest('button')).toHaveAttribute('aria-disabled', 'true')
  })
})
