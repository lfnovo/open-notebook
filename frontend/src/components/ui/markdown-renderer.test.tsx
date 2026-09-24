import { describe, it, expect } from 'vitest'
import { render } from '@testing-library/react'

import { MarkdownRenderer } from './markdown-renderer'

describe('MarkdownRenderer', () => {
  it('renders basic markdown', () => {
    const { container } = render(<MarkdownRenderer>{'# Title\n\nSome **bold** text'}</MarkdownRenderer>)
    expect(container.querySelector('h1')?.textContent).toBe('Title')
    expect(container.querySelector('strong')?.textContent).toBe('bold')
  })

  it('highlights fenced code blocks for registered languages', () => {
    const { container } = render(
      <MarkdownRenderer>{'```python\ndef hello():\n    return 42\n```'}</MarkdownRenderer>
    )
    expect(container.querySelectorAll('span[class*="token"]').length).toBeGreaterThan(0)
  })

  it('falls back to plain text for unknown languages without crashing', () => {
    const { container } = render(
      <MarkdownRenderer>{'```notalanguage\nsome content\n```'}</MarkdownRenderer>
    )
    expect(container.textContent).toContain('some content')
  })

  it('renders inline code without a highlighter block', () => {
    const { container } = render(<MarkdownRenderer>{'Use `npm ci` here'}</MarkdownRenderer>)
    expect(container.querySelector('code')?.textContent).toBe('npm ci')
    expect(container.querySelectorAll('span[class*="token"]').length).toBe(0)
  })

  describe('Mixed-direction content (RTL/LTR)', () => {
    it('renders Arabic text with dir="auto" on root', () => {
      const { container } = render(<MarkdownRenderer>{'مرحبا بالعالم'}</MarkdownRenderer>)
      const root = container.querySelector('div[dir="auto"]')
      expect(root).toBeInTheDocument()
      expect(root?.textContent).toContain('مرحبا')
    })

    it('renders English text with dir="auto" on root', () => {
      const { container } = render(<MarkdownRenderer>{'Hello world'}</MarkdownRenderer>)
      const root = container.querySelector('div[dir="auto"]')
      expect(root).toBeInTheDocument()
      expect(root?.textContent).toContain('Hello world')
    })

    it('renders mixed Arabic and English with dir="auto"', () => {
      const { container } = render(<MarkdownRenderer>{'مرحبا hello world بالعالم'}</MarkdownRenderer>)
      const root = container.querySelector('div[dir="auto"]')
      expect(root).toBeInTheDocument()
    })

    it('renders Arabic text with numbers', () => {
      const { container } = render(<MarkdownRenderer>{'العدد 123 والعدد 456'}</MarkdownRenderer>)
      const root = container.querySelector('div[dir="auto"]')
      expect(root).toBeInTheDocument()
      expect(root?.textContent).toContain('123')
      expect(root?.textContent).toContain('456')
    })

    it('renders Arabic text with URL and forces URL to LTR', () => {
      const { container } = render(<MarkdownRenderer>{'رابط: https://example.com/path'}</MarkdownRenderer>)
      const root = container.querySelector('div[dir="auto"]')
      expect(root).toBeInTheDocument()
      const link = container.querySelector('a[dir="ltr"]')
      expect(link).toBeInTheDocument()
      expect(link?.getAttribute('href')).toBe('https://example.com/path')
    })

    it('renders Arabic text with email and forces email to LTR', () => {
      const { container } = render(<MarkdownRenderer>{'بريد: user@example.com'}</MarkdownRenderer>)
      const root = container.querySelector('div[dir="auto"]')
      expect(root).toBeInTheDocument()
      const link = container.querySelector('a[dir="ltr"]')
      expect(link).toBeInTheDocument()
      expect(link?.getAttribute('href')).toBe('mailto:user@example.com')
    })

    it('renders Arabic text with inline code and forces code to LTR', () => {
      const { container } = render(<MarkdownRenderer>{'الكود: `npm install`'}</MarkdownRenderer>)
      const root = container.querySelector('div[dir="auto"]')
      expect(root).toBeInTheDocument()
      const inlineCode = container.querySelector('code[dir="ltr"]')
      expect(inlineCode).toBeInTheDocument()
      expect(inlineCode?.textContent).toBe('npm install')
    })

    it('renders Arabic text with fenced code block and forces code block to LTR', () => {
      const { container } = render(<MarkdownRenderer>{'الكود:\n```js\nconst x = 1\n```'}</MarkdownRenderer>)
      const root = container.querySelector('div[dir="auto"]')
      expect(root).toBeInTheDocument()
      // Code block is wrapped in SyntaxHighlighter with PreTag="div"
      // The pre component renders a div with dir="ltr" wrapping the highlighter
      const codeWrapper = container.querySelector('div[dir="ltr"]')
      expect(codeWrapper).toBeInTheDocument()
      expect(codeWrapper?.textContent).toContain('const x = 1')
    })

    it('renders Arabic quoted text with blockquote', () => {
      const { container } = render(<MarkdownRenderer>{'> اقتباس عربي\n> سطر ثاني'}</MarkdownRenderer>)
      const root = container.querySelector('div[dir="auto"]')
      expect(root).toBeInTheDocument()
      const blockquote = container.querySelector('blockquote')
      expect(blockquote).toBeInTheDocument()
    })
  })
})
