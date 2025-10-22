import { renderWithProviders, screen } from '@/test-utils'
import { NotebookList } from '../NotebookList'
import { mockNotebooks } from '@/__mocks__/mock-data'
import { vi } from 'vitest'

// Mock Next.js app router hooks used by NotebookCard
vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn() }),
  usePathname: () => '/notebooks',
}))

describe('NotebookList', () => {
  it('renders loading state with spinner', () => {
    const { container } = renderWithProviders(
      <NotebookList notebooks={undefined} isLoading title="Active Notebooks" />
    )

    // Spinner is an SVG with animate-spin class
    const spinner = container.querySelector('svg.animate-spin')
    expect(spinner).toBeInTheDocument()
  })

  it('renders empty state when no notebooks', () => {
    renderWithProviders(
      <NotebookList notebooks={[]} isLoading={false} title="Active Notebooks" />
    )

    expect(screen.getByText('No active notebooks')).toBeInTheDocument()
  })

  it('renders notebooks and toggles collapse', async () => {
    renderWithProviders(
      <NotebookList 
        notebooks={mockNotebooks.multiple} 
        isLoading={false} 
        title="Archived Notebooks" 
        collapsible 
      />
    )

    // Header shows title and count
    expect(screen.getByText('Archived Notebooks')).toBeInTheDocument()
    expect(screen.getByText('(3)')).toBeInTheDocument()

    // Initially collapsed, so cards should not be visible
    expect(screen.queryByText('Alpha Research')).not.toBeInTheDocument()

    // Toggle expand (the first button is the chevron)
    const buttons = screen.getAllByRole('button')
    await (await import('@/test-utils')).userEvent.click(buttons[0])

    // Now the notebooks should be visible
    expect(screen.getByText('Alpha Research')).toBeInTheDocument()
    expect(screen.getByText('Beta Findings')).toBeInTheDocument()
    expect(screen.getByText('Gamma Notes')).toBeInTheDocument()
  })
})
