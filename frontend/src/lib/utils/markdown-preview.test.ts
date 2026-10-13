import { describe, expect, it } from 'vitest'

import { markdownPreview, stripMarkdown } from './markdown-preview'

describe('stripMarkdown', () => {
  it('removes ATX heading markers', () => {
    expect(stripMarkdown('## Title\nSome body text')).toBe('Title Some body text')
    expect(stripMarkdown('# H1 ### H3')).toBe('H1 H3')
  })

  it('removes bold and italic asterisk markers', () => {
    expect(stripMarkdown('**bold** and *italic*')).toBe('bold and italic')
  })

  it('leaves unpaired asterisks (e.g. math) alone', () => {
    expect(stripMarkdown('2 * 3 = 6')).toBe('2 * 3 = 6')
  })

  it('removes underscore emphasis but keeps snake_case identifiers', () => {
    expect(stripMarkdown('__bold__ and _italic_')).toBe('bold and italic')
    expect(stripMarkdown('use snake_case here')).toBe('use snake_case here')
  })

  it('keeps link text and image alt text, drops URLs', () => {
    expect(stripMarkdown('[click here](https://example.com)')).toBe('click here')
    expect(stripMarkdown('![a cat](cat.png)')).toBe('a cat')
  })

  it('keeps code content, drops the fences and backticks', () => {
    expect(stripMarkdown('```python\nprint("hi")\n```')).toBe('print("hi")')
    expect(stripMarkdown('run `npm test` now')).toBe('run npm test now')
  })

  it('removes blockquote and list markers', () => {
    expect(stripMarkdown('> quoted\n- one\n- two\n1. first\n2. second')).toBe(
      'quoted one two first second'
    )
  })

  it('removes table pipes and separator rows', () => {
    expect(stripMarkdown('| Name | Age |\n| --- | --- |\n| Ana | 30 |')).toBe('Name Age Ana 30')
  })

  it('removes horizontal rules and HTML tags', () => {
    expect(stripMarkdown('before\n---\nafter')).toBe('before after')
    expect(stripMarkdown('a <br> b')).toBe('a b')
  })

  it('strips the markers from the issue #1494 example', () => {
    const raw =
      '## Sdělení pro rodiče\nVážení rodiče, rádi bychom vás informovali o ...\n### Zápis do první třídy\n* **Kdy:** 12. dubna'
    const plain = stripMarkdown(raw)
    expect(plain).not.toMatch(/[#*|]/)
    expect(plain).toContain('Kdy: 12. dubna')
    expect(plain).toContain('Zápis do první třídy')
  })

  it('collapses newlines and extra whitespace', () => {
    expect(stripMarkdown('line one\n\nline   two')).toBe('line one line two')
  })
})

describe('markdownPreview', () => {
  it('returns short plain content unchanged', () => {
    expect(markdownPreview('Just a short note.')).toBe('Just a short note.')
  })

  it('strips markdown before truncating to the default 180 chars', () => {
    const content = `## Summary\n\n${'word '.repeat(100)}`
    const preview = markdownPreview(content)
    expect(preview).not.toContain('##')
    expect(preview.endsWith('…')).toBe(true)
    expect(preview.length).toBe(181)
  })

  it('does not append an ellipsis when nothing is truncated', () => {
    const content = '# Title\nShort body.'
    expect(markdownPreview(content)).toBe('Title Short body.')
  })

  it('honors a custom maxLength', () => {
    expect(markdownPreview('abcdefghijklmnopqrstuvwxyz', 10)).toBe('abcdefghij…')
  })

  it('handles empty content', () => {
    expect(markdownPreview('')).toBe('')
  })
})
