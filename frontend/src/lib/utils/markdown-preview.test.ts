import { describe, expect, it } from 'vitest'

import { markdownPreview } from './markdown-preview'

describe('markdownPreview', () => {
  it('strips headings, bold and list markers from a model answer', () => {
    const md = [
      '## Sdělení pro rodiče',
      '',
      'Vážení rodiče,',
      '',
      '### Zápis do první třídy',
      '* **Kdy:** 12. dubna od 14:00 do 17:00',
      '* **Kde:** budova A',
    ].join('\n')

    expect(markdownPreview(md, 500)).toBe(
      'Sdělení pro rodiče Vážení rodiče, Zápis do první třídy Kdy: 12. dubna od 14:00 do 17:00 Kde: budova A'
    )
  })

  it('keeps link labels and image alt text, drops the URLs', () => {
    expect(markdownPreview('See [the docs](https://example.com/x) and ![logo](a.png).')).toBe(
      'See the docs and logo.'
    )
  })

  it('drops fenced code blocks and unwraps inline code', () => {
    expect(markdownPreview('Run `make api` first.\n```bash\nmake start-all\n```\nThen open it.')).toBe(
      'Run make api first. Then open it.'
    )
  })

  it('turns tables into readable text without pipes and separator rows', () => {
    const md = '| Úkol | Kdo |\n| :--- | :--- |\n| Zvonek | školník |'
    expect(markdownPreview(md)).toBe('Úkol Kdo Zvonek školník')
  })

  it('keeps snake_case identifiers and list numbering text intact', () => {
    expect(markdownPreview('1. Open source_insight and my_file_name now')).toBe(
      'Open source_insight and my_file_name now'
    )
  })

  it('handles emphasis, quotes and strikethrough', () => {
    expect(markdownPreview('> *Note:* __really__ ~~old~~ _new_')).toBe('Note: really old new')
  })

  it('truncates long text with an ellipsis and leaves short text alone', () => {
    const long = 'word '.repeat(100)
    const out = markdownPreview(long, 20)
    expect(out.endsWith('…')).toBe(true)
    expect(out.length).toBeLessThanOrEqual(21)
    expect(markdownPreview('short text', 20)).toBe('short text')
  })

  it('returns an empty string for empty or markup-only input', () => {
    expect(markdownPreview('')).toBe('')
    expect(markdownPreview('---')).toBe('')
  })
})
