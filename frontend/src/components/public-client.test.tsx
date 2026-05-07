import { fireEvent, render, screen, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { PublicClient } from './public-client'

const { authState, replace } = vi.hoisted(() => ({
  authState: {
    hasHydrated: true,
    isAuthenticated: false,
    token: null as string | null,
  },
  replace: vi.fn(),
}))

vi.mock('next/navigation', () => ({
  useRouter: () => ({ replace }),
}))

vi.mock('@/lib/stores/auth-store', () => ({
  useAuthStore: () => authState,
}))

vi.mock('@/lib/hooks/use-translation', () => ({
  useTranslation: () => ({
    t: {
      public: {
        discover: '发现',
        title: '公开内容',
        description: '浏览公开分享的笔记本和来源',
        notebooks: '笔记本',
        sources: '来源',
        searchPlaceholder: '搜索公开内容...',
      },
    },
  }),
}))

vi.mock('@/components/public/PublicNotebooks', () => ({
  PublicNotebooks: ({ rankingMode }: { rankingMode: string }) => (
    <div>公开笔记本列表:{rankingMode}</div>
  ),
}))

vi.mock('@/components/public/PublicSources', () => ({
  PublicSources: ({ rankingMode }: { rankingMode: string }) => (
    <div>公开来源列表:{rankingMode}</div>
  ),
}))

describe('PublicClient', () => {
  beforeEach(() => {
    authState.hasHydrated = true
    authState.isAuthenticated = false
    authState.token = null
    replace.mockClear()
  })

  it('provides clear guest guidance with back, login, and registration actions', () => {
    render(<PublicClient />)

    const banner = screen.getByRole('banner')
    const primaryNav = within(banner).getByRole('navigation', { name: '主导航' })
    const accountNav = within(banner).getByRole('navigation', { name: '账户操作' })

    expect(within(primaryNav).getByRole('link', { name: '返回首页' })).toHaveAttribute('href', '/')
    expect(within(accountNav).getByRole('link', { name: '登录' })).toHaveAttribute('href', '/login')
    expect(within(accountNav).getByRole('link', { name: '注册' })).toHaveAttribute('href', '/register')
    expect(accountNav.className).toContain('border-l')
    expect(screen.getByRole('heading', { name: '公开内容' })).toBeInTheDocument()
  })

  it('redirects authenticated users to the dashboard discover page', () => {
    authState.isAuthenticated = true
    authState.token = 'token'

    render(<PublicClient />)

    expect(replace).toHaveBeenCalledWith('/discover')
    expect(screen.queryByRole('heading', { name: '公开内容' })).not.toBeInTheDocument()
  })

  it('lets guests switch public ranking modes', async () => {
    render(<PublicClient />)

    expect(screen.getByText('公开笔记本列表:most_visited')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: '引用最多' }))
    expect(screen.getByText('公开笔记本列表:most_referenced')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: '最热访问' }))
    expect(screen.getByText('公开笔记本列表:most_visited')).toBeInTheDocument()
  })
})
