import { describe, it, expect } from 'vitest'
import { render } from '@testing-library/react'
import MarkdownPreview from '@uiw/react-markdown-preview'

import { PREVIEW_OPTIONS } from './markdown-editor'

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

  it('still renders GFM tables, task lists, and safe links', () => {
    const { container } = renderPreview(
      '| a | b |\n|---|---|\n| 1 | 2 |\n\n- [x] done\n- [ ] todo\n\n[a link](https://example.com)'
    )
    expect(container.querySelector('table')).not.toBeNull()
    expect(container.querySelectorAll('input[type="checkbox"]').length).toBe(2)
    expect(container.querySelector('a')?.getAttribute('href')).toBe('https://example.com')
  })
})
