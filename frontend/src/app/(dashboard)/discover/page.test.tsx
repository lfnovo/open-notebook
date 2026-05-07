import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import DiscoverPage from './page'

vi.mock('@/components/public-client', () => ({
  PublicContentExplorer: () => <div data-testid="public-content-explorer" />,
}))

describe('DiscoverPage', () => {
  it('renders only the public content explorer as a dashboard page body', () => {
    render(<DiscoverPage />)

    expect(screen.getByTestId('public-content-explorer')).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Public Content' })).not.toBeInTheDocument()
    expect(
      screen.queryByText('Browse publicly shared notebooks and sources')
    ).not.toBeInTheDocument()
    expect(screen.queryByRole('banner')).not.toBeInTheDocument()
  })
})
