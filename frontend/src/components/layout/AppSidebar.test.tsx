/* eslint-disable @typescript-eslint/no-explicit-any */
import { render, screen, fireEvent } from '@testing-library/react'
import { beforeEach, describe, it, expect, vi } from 'vitest'
import { AppSidebar } from './AppSidebar'
import { useSidebarStore } from '@/lib/stores/sidebar-store'
import { useAuthStore } from '@/lib/stores/auth-store'
import { useCanManageTeams } from '@/lib/hooks/use-teams'

// Mock Tooltip components to avoid Radix UI async issues in tests
vi.mock('@/components/ui/tooltip', () => ({
  TooltipProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  Tooltip: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  TooltipTrigger: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  TooltipContent: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}))

vi.mock('@/lib/hooks/use-teams', () => ({
  useCanManageTeams: vi.fn(() => false),
}))
// But setup.ts has some basic mocks, let's see.

describe('AppSidebar', () => {
  beforeEach(() => {
    useAuthStore.setState({ role: null })
    vi.mocked(useCanManageTeams).mockReturnValue(false)
    vi.mocked(useSidebarStore).mockReturnValue({
      isCollapsed: false,
      toggleCollapse: vi.fn(),
    } as any)
  })

  it('renders correctly when expanded', () => {
    render(<AppSidebar />)
    
    // Check for logo or app name (using actual locale value)
    expect(screen.getByText(/Lumina™ | Yinshi AI/i)).toBeDefined()
    
    // Check for navigation items (using actual locale values)
    expect(screen.getByText(/Sources/i)).toBeDefined()
    expect(screen.getByText(/Notebooks/i)).toBeDefined()
  })

  it('toggles collapse state when clicking handle', () => {
    const toggleCollapse = vi.fn()
    vi.mocked(useSidebarStore).mockReturnValue({
      isCollapsed: false,
      toggleCollapse,
    } as any)

    render(<AppSidebar />)
    
    // The collapse button has ChevronLeft icon when expanded
    // The collapse button has ChevronLeft icon when expanded
    // const toggleButton = screen.getAllByRole('button')[0]
    // Let's use more specific selector if possible, but AppSidebar has many buttons
    // Actually, line 147 has the button
    
    // Use data-testid for reliable selection
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
    expect(screen.queryByText(/Lumina™ | Yinshi AI/i)).toBeNull()
  })

  it('shows profile for all users and team management for admins', () => {
    useAuthStore.setState({ role: 'admin' })

    render(<AppSidebar />)

    expect(screen.getByText('Profile')).toBeInTheDocument()
    expect(screen.getByText('Teams')).toBeInTheDocument()
  })

  it('keeps profile visible for non-admin users', () => {
    useAuthStore.setState({ role: 'user' })

    render(<AppSidebar />)

    expect(screen.getByText('Profile')).toBeInTheDocument()
    expect(screen.queryByText('Teams')).not.toBeInTheDocument()
  })

  it('places admin management links in their own sidebar group for admins', () => {
    useAuthStore.setState({ role: 'admin' })

    render(<AppSidebar />)

    const adminGroup = screen.getByRole('group', { name: 'Admin' })
    expect(adminGroup).toHaveTextContent('Users')
    expect(adminGroup).toHaveTextContent('Teams')
    expect(adminGroup).toHaveTextContent('Audit Log')

    const manageGroup = screen.getByRole('group', { name: 'Manage' })
    expect(manageGroup).not.toHaveTextContent('Users')
    expect(manageGroup).not.toHaveTextContent('Teams')
    expect(manageGroup).not.toHaveTextContent('Audit Log')
  })

  it('shows system management links for system admins', () => {
    useAuthStore.setState({ role: 'admin' })

    render(<AppSidebar />)

    expect(screen.getByText('Models')).toBeInTheDocument()
    expect(screen.getByText('Transformations')).toBeInTheDocument()
    expect(screen.getByText('Settings')).toBeInTheDocument()
    expect(screen.getByText('Advanced')).toBeInTheDocument()
    expect(screen.getByText('Users')).toBeInTheDocument()
    expect(screen.getByText('Teams')).toBeInTheDocument()
    expect(screen.getByText('Audit Log')).toBeInTheDocument()
  })

  it('shows only team management for team managers', () => {
    useAuthStore.setState({ role: 'user' })
    vi.mocked(useCanManageTeams).mockReturnValue(true)

    render(<AppSidebar />)

    expect(screen.getByText('Teams')).toBeInTheDocument()
    expect(screen.queryByText('Models')).not.toBeInTheDocument()
    expect(screen.queryByText('Transformations')).not.toBeInTheDocument()
    expect(screen.queryByText('Settings')).not.toBeInTheDocument()
    expect(screen.queryByText('Advanced')).not.toBeInTheDocument()
    expect(screen.queryByText('Users')).not.toBeInTheDocument()
    expect(screen.queryByText('Audit Log')).not.toBeInTheDocument()
  })

  it('hides management links for regular users', () => {
    useAuthStore.setState({ role: 'user' })

    render(<AppSidebar />)

    expect(screen.queryByText('Models')).not.toBeInTheDocument()
    expect(screen.queryByText('Transformations')).not.toBeInTheDocument()
    expect(screen.queryByText('Settings')).not.toBeInTheDocument()
    expect(screen.queryByText('Advanced')).not.toBeInTheDocument()
    expect(screen.queryByText('Users')).not.toBeInTheDocument()
    expect(screen.queryByText('Teams')).not.toBeInTheDocument()
    expect(screen.queryByText('Audit Log')).not.toBeInTheDocument()
  })

  it('links sidebar public discovery to the dashboard discover route', () => {
    render(<AppSidebar />)

    expect(screen.getByRole('link', { name: 'Discover' })).toHaveAttribute('href', '/discover')
  })
})
