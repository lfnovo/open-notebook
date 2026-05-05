import { render, screen } from '@testing-library/react'
import type { MouseEventHandler, ReactNode } from 'react'
import { describe, expect, it, vi } from 'vitest'
import { SourceListResponse } from '@/lib/types/api'
import { SourceCard } from './SourceCard'

vi.mock('@/lib/hooks/use-sources', () => ({
  useSourceStatus: vi.fn(() => ({
    data: undefined,
    isLoading: false,
  })),
}))

vi.mock('@/components/common/ContextToggle', () => ({
  ContextToggle: () => null,
}))

vi.mock('@/components/ui/dropdown-menu', () => ({
  DropdownMenu: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  DropdownMenuTrigger: ({ children }: { children: ReactNode }) => <>{children}</>,
  DropdownMenuContent: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  DropdownMenuSeparator: () => <hr />,
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

const baseSource: SourceListResponse = {
  id: 'source:one',
  title: 'One',
  topics: [],
  asset: null,
  embedded: true,
  embedded_chunks: 1,
  kg_extracted: false,
  insights_count: 0,
  reference_count: 0,
  created: '2026-05-05T00:00:00Z',
  updated: '2026-05-05T00:00:00Z',
  owner_id: 'app_user:owner',
  visibility: 'private',
}

describe('SourceCard', () => {
  it('disables delete when no delete handler is provided', () => {
    render(<SourceCard source={baseSource} />)

    expect(screen.getByText('Delete Source').closest('button')).toHaveAttribute(
      'aria-disabled',
      'true'
    )
  })
})
