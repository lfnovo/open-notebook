import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { SelectLinksStep } from './SelectLinksStep'
import { useDiscoverLinks } from '@/lib/hooks/use-sources'

// useTranslation is mocked globally in setup.ts (t returns the key string)
vi.mock('@/lib/hooks/use-sources', () => ({
  useDiscoverLinks: vi.fn(),
}))

const mockHook = useDiscoverLinks as unknown as ReturnType<typeof vi.fn>

describe('SelectLinksStep', () => {
  beforeEach(() => {
    mockHook.mockReset()
  })

  it('shows a loading state while scanning', () => {
    mockHook.mockReturnValue({ data: undefined, isLoading: true, isError: false, refetch: vi.fn() })
    render(
      <SelectLinksStep sourceUrl="https://example.com" selectedLinks={[]} onSelectedChange={vi.fn()} onSkip={vi.fn()} />
    )
    expect(screen.getByText('sources.scanningLinks')).toBeInTheDocument()
  })

  it('renders an error with a skip action on failure', () => {
    const onSkip = vi.fn()
    mockHook.mockReturnValue({ data: undefined, isLoading: false, isError: true, refetch: vi.fn() })
    render(
      <SelectLinksStep sourceUrl="https://example.com" selectedLinks={[]} onSelectedChange={vi.fn()} onSkip={onSkip} />
    )
    expect(screen.getByText('sources.discoverLinksError')).toBeInTheDocument()
    fireEvent.click(screen.getByText('sources.skipImportOriginal'))
    expect(onSkip).toHaveBeenCalledTimes(1)
  })

  it('renders candidates and toggles selection', () => {
    const onSelectedChange = vi.fn()
    mockHook.mockReturnValue({
      data: {
        source_url: 'https://example.com',
        count: 2,
        links: [
          { url: 'https://example.com/a', text: 'A', same_domain: true },
          { url: 'https://other.com/b', text: 'B', same_domain: false },
        ],
      },
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    })
    render(
      <SelectLinksStep sourceUrl="https://example.com" selectedLinks={[]} onSelectedChange={onSelectedChange} onSkip={vi.fn()} />
    )
    // The link text is shown
    expect(screen.getByText('A')).toBeInTheDocument()
    expect(screen.getByText('B')).toBeInTheDocument()
    // Clicking "select all" selects both
    fireEvent.click(screen.getByText('sources.selectAll'))
    expect(onSelectedChange).toHaveBeenCalledWith([
      'https://example.com/a',
      'https://other.com/b',
    ])
  })

  it('select same-site chooses only same_domain links', () => {
    const onSelectedChange = vi.fn()
    mockHook.mockReturnValue({
      data: {
        source_url: 'https://example.com',
        count: 2,
        links: [
          { url: 'https://example.com/a', text: 'A', same_domain: true },
          { url: 'https://other.com/b', text: 'B', same_domain: false },
        ],
      },
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    })
    render(
      <SelectLinksStep sourceUrl="https://example.com" selectedLinks={[]} onSelectedChange={onSelectedChange} onSkip={vi.fn()} />
    )
    fireEvent.click(screen.getByText('sources.selectSameDomain'))
    expect(onSelectedChange).toHaveBeenCalledWith(['https://example.com/a'])
  })
})
