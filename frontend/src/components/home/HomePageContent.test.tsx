import { render, screen, within } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { HomePageContent } from './HomePageContent'

vi.mock('@/components/public-client', () => ({
  PublicContentExplorer: () => <div data-testid="public-content-explorer" />,
}))

describe('HomePageContent', () => {
  it('links to public content from the top navigation without embedding the public explorer or footer public link', () => {
    render(<HomePageContent />)

    const banner = screen.getByRole('banner')
    expect(within(banner).getByRole('link', { name: '公开内容' })).toHaveAttribute('href', '/public')
    expect(screen.queryByTestId('public-content-explorer')).not.toBeInTheDocument()

    const footer = screen.getByRole('contentinfo')
    expect(within(footer).queryByRole('link', { name: '公开内容' })).not.toBeInTheDocument()
  })
})
