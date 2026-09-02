import { describe, it, expect } from 'vitest'
import { render } from '@testing-library/react'
import MarkdownPreview from '@uiw/react-markdown-preview'
import { readFileSync } from 'node:fs'
import { join } from 'node:path'

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
  it('restores top-level list markers without overriding nested and task lists', () => {
    const appCss = readFileSync(join(process.cwd(), 'src/app/globals.css'), 'utf8')
    const previewCss = readFileSync(
      join(process.cwd(), 'node_modules/@uiw/react-markdown-preview/markdown.css'),
      'utf8'
    )
    const markerRules = ['ul', 'ol'].map((tag) => {
      const selector = `.w-md-editor-preview :where(.wmde-markdown ${tag})`
      const escapedSelector = selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
      const match = appCss.match(new RegExp(`${escapedSelector}\\s*\\{[^}]+\\}`))
      expect(match, `missing marker rule for ${tag}`).not.toBeNull()
      return match![0]
    })
    expect(previewCss).toMatch(
      /\.wmde-markdown ol ol,\s*\.wmde-markdown ul ol\s*\{[^}]*list-style-type:\s*lower-roman/
    )
    const style = document.createElement('style')
    style.textContent = `ol, ul, menu { list-style: none; }\n${previewCss}\n${markerRules.join('\n')}`
    document.head.appendChild(style)

    try {
      const { container } = render(
        <div className="w-md-editor-preview">
          <MarkdownPreview
            source={'- Bullet\n  1. Nested ordered\n\n1. Ordered\n\n- [x] Task'}
            remarkPlugins={PREVIEW_OPTIONS.remarkPlugins}
            rehypePlugins={PREVIEW_OPTIONS.rehypePlugins}
          />
        </div>
      )
      const markdown = container.querySelector('.wmde-markdown')!
      const topLevelUl = markdown.querySelector(':scope > ul:not(.contains-task-list)')!
      const topLevelOl = markdown.querySelector(':scope > ol')!
      const taskItem = markdown.querySelector('li.task-list-item')!

      expect(getComputedStyle(topLevelUl).listStyleType).toBe('disc')
      expect(getComputedStyle(topLevelOl).listStyleType).toBe('decimal')
      expect(getComputedStyle(taskItem).listStyleType).toBe('none')
    } finally {
      style.remove()
    }
  })

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
