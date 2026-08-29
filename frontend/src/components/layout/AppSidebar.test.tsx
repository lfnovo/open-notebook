/* eslint-disable @typescript-eslint/no-explicit-any */
import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { AppSidebar } from './AppSidebar'
import { useSidebarStore } from '@/lib/stores/sidebar-store'
import { useIsDesktop } from '@/lib/hooks/use-media-query'

// Mock Tooltip components to avoid Radix UI async issues in tests
vi.mock('@/components/ui/tooltip', () => ({
  TooltipProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  Tooltip: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  TooltipTrigger: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  TooltipContent: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}))

// setup.ts's global matchMedia mock always reports no match, which would make
// every test see the below-desktop (forced-collapsed) branch. Default to
// desktop here; the mobile test below overrides it explicitly.
vi.mock('@/lib/hooks/use-media-query', () => ({
  useIsDesktop: vi.fn(() => true),
}))

describe('AppSidebar', () => {
  it('renders correctly when expanded', () => {
    render(<AppSidebar />)

    // With mocked t() returning keys, check for translation key strings
    expect(screen.getByText('common.appName')).toBeDefined()
    expect(screen.getByText('navigation.sources')).toBeDefined()
    expect(screen.getByText('navigation.notebooks')).toBeDefined()
  })

  it('toggles collapse state when clicking handle', () => {
    const toggleCollapse = vi.fn()
    vi.mocked(useSidebarStore).mockReturnValue({
      isCollapsed: false,
      toggleCollapse,
    } as any)

    render(<AppSidebar />)

    fireEvent.click(screen.getByTestId('sidebar-toggle'))

    expect(toggleCollapse).toHaveBeenCalled()
  })

  it('shows collapsed view when isCollapsed is true', () => {
    vi.mocked(useSidebarStore).mockReturnValue({
      isCollapsed: true,
      toggleCollapse: vi.fn(),
    } as any)

    render(<AppSidebar />)

    // In collapsed mode, app name shouldn't be visible (as text)
    expect(screen.queryByText('common.appName')).toBeNull()
  })

  it('forces the collapsed view below the desktop breakpoint even if the stored preference is expanded', () => {
    vi.mocked(useSidebarStore).mockReturnValue({
      isCollapsed: false,
      toggleCollapse: vi.fn(),
    } as any)
    vi.mocked(useIsDesktop).mockReturnValue(false)

    render(<AppSidebar />)

    // A phone-width viewport can't fit the 256px expanded sidebar - it must
    // render collapsed regardless of what's persisted from a desktop visit.
    expect(screen.queryByText('common.appName')).toBeNull()
    // No expand toggle either: :hover never fires on touch, and there's no
    // room to expand into on mobile anyway.
    expect(screen.queryByTestId('sidebar-toggle')).toBeNull()

    vi.mocked(useIsDesktop).mockReturnValue(true)
  })
})
