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
    const primaryNav = within(banner).getByRole('navigation', { name: '主导航' })
    const accountNav = within(banner).getByRole('navigation', { name: '账户操作' })

    expect(within(primaryNav).getByRole('link', { name: '公开内容' })).toHaveAttribute('href', '/public')
    expect(within(accountNav).getByRole('link', { name: '登录' })).toHaveAttribute('href', '/login')
    expect(within(accountNav).getByRole('link', { name: '注册' })).toHaveAttribute('href', '/register')
    expect(accountNav.className).toContain('border-l')
    expect(screen.queryByTestId('public-content-explorer')).not.toBeInTheDocument()

    const footer = screen.getByRole('contentinfo')
    expect(within(footer).queryByRole('link', { name: '公开内容' })).not.toBeInTheDocument()
  })
})
