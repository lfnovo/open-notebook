import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { PublicClient } from './public-client'

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
  PublicNotebooks: () => <div>公开笔记本列表</div>,
}))

vi.mock('@/components/public/PublicSources', () => ({
  PublicSources: () => <div>公开来源列表</div>,
}))

describe('PublicClient', () => {
  it('provides clear guest guidance with back, login, and registration actions', () => {
    render(<PublicClient />)

    expect(screen.getByRole('link', { name: '返回首页' })).toHaveAttribute('href', '/')
    expect(screen.getByRole('link', { name: '登录' })).toHaveAttribute('href', '/login')
    expect(screen.getByRole('link', { name: '注册' })).toHaveAttribute('href', '/register')
    expect(screen.getByRole('heading', { name: '公开内容' })).toBeInTheDocument()
  })
})
