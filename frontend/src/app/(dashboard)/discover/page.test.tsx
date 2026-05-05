import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import DiscoverPage from './page'

vi.mock('@/components/public-client', () => ({
  PublicContentExplorer: () => <div data-testid="public-content-explorer" />,
}))

describe('DiscoverPage', () => {
  it('renders the public content explorer as a dashboard page body', () => {
    render(<DiscoverPage />)

    expect(screen.getByRole('heading', { name: 'Public Content' })).toBeInTheDocument()
    expect(screen.getByTestId('public-content-explorer')).toBeInTheDocument()
    expect(screen.queryByRole('banner')).not.toBeInTheDocument()
  })
})
