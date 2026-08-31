import { afterEach, describe, it, expect, vi } from 'vitest'
import { act, render, screen } from '@testing-library/react'
import MarkdownPreview from '@uiw/react-markdown-preview'

import { useThemeStore } from '@/lib/stores/theme-store'
import { MarkdownEditor, PREVIEW_OPTIONS } from './markdown-editor'

vi.mock('next/dynamic', () => ({
  default: () =>
    function MockMarkdownEditor(props: { 'data-color-mode'?: string }) {
      return <div data-testid="md-editor" data-color-mode={props['data-color-mode']} />
    },
}))

// MarkdownEditor's live preview renders through @uiw/react-markdown-preview,
// which parses raw HTML in the markdown source into real elements (its `raw`
// default). Notes can hold AI-generated content that echoes an indirect
// prompt injection, so anything rendered here must not let that raw HTML
// become a live <iframe>/<script>/<style>/javascript: URL - while still
// preserving math, syntax highlighting, and GFM, which are real features.
// These tests exercise the actual PREVIEW_OPTIONS MarkdownEditor uses, via
// the same underlying preview component, rather than a hand-rolled pipeline.
function renderPreview(source: string) {
  return render(
    <MarkdownPreview
      source={source}
      remarkPlugins={PREVIEW_OPTIONS.remarkPlugins}
      rehypePlugins={PREVIEW_OPTIONS.rehypePlugins}
    />
  )
}

describe('MarkdownEditor theme', () => {
  afterEach(() => {
    useThemeStore.getState().setTheme('system')
  })

  it('follows theme changes without remounting', () => {
    act(() => useThemeStore.getState().setTheme('light'))
    render(<MarkdownEditor />)
    expect(screen.getByTestId('md-editor')).toHaveAttribute('data-color-mode', 'light')

    act(() => useThemeStore.getState().setTheme('dark'))
    expect(screen.getByTestId('md-editor')).toHaveAttribute('data-color-mode', 'dark')
  })
})

describe('MarkdownEditor preview sanitization', () => {
  it('strips a raw <iframe> to a live, embeddable element', () => {
    const { container } = renderPreview('before <iframe src="https://evil.example"></iframe> after')
    expect(container.querySelector('iframe')).toBeNull()
    expect(container.innerHTML).not.toContain('evil.example')
  })

  it('strips raw <script> content', () => {
    const { container } = renderPreview('before <script>window.__pwned = true</script> after')
    expect(container.innerHTML).not.toContain('__pwned')
  })

  it('strips a raw <style> element (CSS-based UI redress)', () => {
    // The style tag itself must not survive as a live element - its text
    // content becoming inert prose (rather than a stylesheet) is fine.
    const { container } = renderPreview('before <style>body{display:none}</style> after')
    expect(container.querySelector('style')).toBeNull()
  })

  it('strips javascript: URLs from links', () => {
    const { container } = renderPreview('[click me](javascript:alert(1))')
    const link = container.querySelector('a')
    expect(link?.getAttribute('href') ?? '').not.toContain('javascript:')
  })

  it('does not execute inline event-handler attributes on parsed raw elements', () => {
    const { container } = renderPreview('<img src="x" onerror="window.__pwned = true">')
    expect(container.innerHTML).not.toContain('onerror')
  })

  it('still renders KaTeX math with its classes and MathML intact', () => {
    const { container } = renderPreview('Inline math $x^2 + y^2 = z^2$')
    expect(container.querySelector('.katex')).not.toBeNull()
    expect(container.querySelector('.katex-mathml math')).not.toBeNull()
  })

  it('still syntax-highlights fenced code blocks', () => {
    const { container } = renderPreview('```python\ndef hello():\n    return 42\n```')
    expect(container.querySelectorAll('span[class*="token"]').length).toBeGreaterThan(0)
  })

  it('still renders the code-block copy button the library injects', () => {
    // The preview library's rehypeRewrite injects div.copied[data-code] with
    // two octicon SVGs before user plugins run; the sanitize schema must let
    // exactly that markup through or the copy feature dies silently.
    const { container } = renderPreview('```js\nconst a = 1;\n```')
    const button = container.querySelector('pre div.copied')
    expect(button).not.toBeNull()
    expect(button?.getAttribute('data-code')).toContain('const a = 1;')
    expect(button?.querySelector('svg.octicon-copy')).not.toBeNull()
    expect(button?.querySelector('svg.octicon-check')).not.toBeNull()
  })

  it('still renders GFM tables, task lists, and safe links', () => {
    const { container } = renderPreview(
      '| a | b |\n|---|---|\n| 1 | 2 |\n\n- [x] done\n- [ ] todo\n\n[a link](https://example.com)'
    )
    expect(container.querySelector('table')).not.toBeNull()
    expect(container.querySelectorAll('input[type="checkbox"]').length).toBe(2)
    expect(container.querySelector('a')?.getAttribute('href')).toBe('https://example.com')
  })
})
