import { fireEvent, render, screen, within } from '@testing-library/react'
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
    expect(within(footer).getByText('© 2026 成都寅时智能')).toBeInTheDocument()
    expect(within(footer).getByRole('button', { name: '隐私政策' })).toBeInTheDocument()
    expect(within(footer).getByRole('button', { name: '法律声明' })).toBeInTheDocument()
    expect(within(footer).getByRole('link', { name: '蜀ICP备2026017298号' })).toHaveAttribute(
      'href',
      'https://beian.miit.gov.cn/',
    )
    expect(
      within(footer).getByRole('link', { name: /川公网安备51019002009363号/ }),
    ).toHaveAttribute(
      'href',
      'https://beian.mps.gov.cn/#/query/webSearch?code=51019002009363',
    )
  })

  it('opens the copied privacy policy and legal statement from the footer', async () => {
    render(<HomePageContent />)

    fireEvent.click(screen.getByRole('button', { name: '隐私政策' }))
    expect(screen.getByRole('dialog', { name: '隐私政策' })).toHaveTextContent(
      '本隐私政策适用于本网站所有访问用户',
    )

    fireEvent.click(screen.getByRole('button', { name: '我知道了' }))
    fireEvent.click(screen.getByRole('button', { name: '法律声明' }))
    expect(screen.getByRole('dialog', { name: '法律声明' })).toHaveTextContent(
      '本站所有内容版权归本企业所有',
    )
  })
})
