import { renderWithProviders, screen } from '@/test-utils'
import NotebooksPage from '../page'
import { vi } from 'vitest'
import { notebooksApi } from '@/lib/api/notebooks'
import { mockNotebooks } from '@/__mocks__/mock-data'

// Lightly mock AppShell to avoid rendering sidebar and heavy layout
vi.mock('@/components/layout/AppShell', () => ({
  AppShell: ({ children }: { children: React.ReactNode }) => <div data-testid="app-shell">{children}</div>,
}))

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn() }),
  usePathname: () => '/notebooks',
}))

describe('NotebooksPage', () => {
  beforeEach(() => {
    vi.spyOn(notebooksApi, 'list').mockImplementation(async (params?: { archived?: boolean }) => {
      if (params?.archived) return mockNotebooks.archived
      return mockNotebooks.multiple
    })
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('renders active and archived notebooks and filters by search term', async () => {
    const { user } = renderWithProviders(<NotebooksPage />)

    // Wait for lists to render
    expect(await screen.findByText('Active Notebooks')).toBeInTheDocument()
    expect(screen.getByText('Archived Notebooks')).toBeInTheDocument()

    // Active notebooks rendered
    expect(screen.getByText('Alpha Research')).toBeInTheDocument()
    expect(screen.getByText('Beta Findings')).toBeInTheDocument()

    // Archived notebooks rendered when expanded by default? Archived list is collapsible=false by default here
    // It should render count/heading; card visibility is handled in NotebookList tests

    // Search filters both lists
    const search = screen.getByPlaceholderText(/search notebooks/i)
    await user.type(search, 'alp')

    // Only Alpha remains in active list
    expect(screen.getByText('Alpha Research')).toBeInTheDocument()
    expect(screen.queryByText('Beta Findings')).not.toBeInTheDocument()

    // Archived list shows empty search state
    expect(screen.getByText('No archived notebooks match your search')).toBeInTheDocument()
  })
})
