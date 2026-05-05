/* eslint-disable @typescript-eslint/no-explicit-any */
import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import AuditLogPage from './page'
import { useAuditLog } from '@/lib/hooks/use-audit-log'

vi.mock('@/lib/hooks/use-audit-log', () => ({
  useAuditLog: vi.fn(),
}))

describe('AuditLogPage', () => {
  beforeEach(() => {
    vi.mocked(useAuditLog).mockReturnValue({
      data: {
        items: [
          {
            id: 'audit_log:1',
            action: 'team.created',
            actor_username: 'admin',
            actor_id: 'app_user:admin',
            target_type: 'team',
            target_id: 'team:research',
            metadata: { slug: 'research' },
            created: '2026-05-05T00:00:00Z',
          },
        ],
        limit: 50,
        offset: 0,
        total: 125,
      },
      isLoading: false,
      error: null,
    } as any)
  })

  it('renders a paged and scrollable audit log table', () => {
    render(<AuditLogPage />)

    expect(screen.getByText('team.created')).toBeInTheDocument()
    expect(screen.getByText('1-50 / 125')).toBeInTheDocument()
    expect(screen.getByTestId('audit-log-scroll')).toHaveClass('overflow-auto')
  })

  it('loads the next page lazily when next is clicked', () => {
    render(<AuditLogPage />)

    fireEvent.click(screen.getByRole('button', { name: 'Next' }))

    expect(useAuditLog).toHaveBeenLastCalledWith({
      actor_id: undefined,
      action: undefined,
      target_id: undefined,
      limit: 50,
      offset: 50,
    })
  })
})
